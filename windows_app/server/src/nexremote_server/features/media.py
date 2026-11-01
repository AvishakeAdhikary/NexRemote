"""Media playback (Windows GSMTC) and master volume (Core Audio)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from nexremote_server.features.base import Feature
from nexremote_server.protocol.jsonutil import get_int, get_str

log = logging.getLogger(__name__)

VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_STOP = 0xB2
VK_MEDIA_NEXT = 0xB0
VK_MEDIA_PREV = 0xB1
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
MEDIA_INFO_INTERVAL_SECONDS = 1.5


def _with_endpoint(fn):
    """Run fn(IAudioEndpointVolume) on a COM-initialised worker thread; None if unavailable."""

    def run():
        try:
            import comtypes
            from pycaw.pycaw import AudioUtilities
        except ImportError:
            return None
        comtypes.CoInitialize()
        try:
            endpoint = AudioUtilities.GetSpeakers().EndpointVolume
            return fn(endpoint)
        except Exception:
            log.debug("endpoint volume unavailable", exc_info=True)
            return None
        finally:
            comtypes.CoUninitialize()

    return asyncio.to_thread(run)


async def _session():
    try:
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Manager
    except ImportError:
        return None
    try:
        manager = await Manager.request_async()
        return manager.get_current_session()
    except Exception:
        log.debug("GSMTC unavailable", exc_info=True)
        return None


def _ms(value: Any) -> int:
    # winrt maps TimeSpan to datetime.timedelta
    try:
        return int(value.total_seconds() * 1000)
    except AttributeError:
        return int(value or 0) // 10_000


class MediaFeature(Feature):
    message_types = ("media_control",)

    def __init__(self, ctx, input_controller) -> None:
        super().__init__(ctx)
        self.input = input_controller

    def _media_key(self, vk: int) -> None:
        self.input.backend.key(vk, up=False)
        self.input.backend.key(vk, up=True)

    async def _invoke(self, method: str) -> bool:
        session = await _session()
        if session is None:
            return False
        try:
            return bool(await getattr(session, method)())
        except Exception:
            return False

    async def handle(self, session, msg_type: str, msg: dict[str, Any]) -> None:
        if not session.has_task("media_info"):
            session.run_task("media_info", self._push_loop(session))
        reply = await self.handle_action(msg)
        if reply is not None:
            await session.send_encrypted(reply)

    async def handle_action(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        action = get_str(msg, "action")
        try:
            match action:
                case "play":
                    if not await self._invoke("try_play_async"):
                        self._media_key(VK_MEDIA_PLAY_PAUSE)
                case "pause":
                    if not await self._invoke("try_pause_async"):
                        self._media_key(VK_MEDIA_PLAY_PAUSE)
                case "stop":
                    if not await self._invoke("try_stop_async"):
                        self._media_key(VK_MEDIA_STOP)
                case "next":
                    if not await self._invoke("try_skip_next_async"):
                        self._media_key(VK_MEDIA_NEXT)
                case "previous":
                    if not await self._invoke("try_skip_previous_async"):
                        self._media_key(VK_MEDIA_PREV)
                case "volume":
                    await self._set_volume(get_int(msg, "value", 50))
                case "mute_toggle":
                    if await _with_endpoint(lambda ep: ep.SetMute(not ep.GetMute(), None) or True) is None:
                        self._media_key(VK_VOLUME_MUTE)
                case "volume_up":
                    self._media_key(VK_VOLUME_UP)
                case "volume_down":
                    self._media_key(VK_VOLUME_DOWN)
                case "seek":
                    await self._seek(get_int(msg, "position"))
                case "get_info":
                    return await self.full_state()
        except Exception:
            log.debug("media action %s failed", action, exc_info=True)
        return None

    async def _set_volume(self, value: int) -> None:
        value = max(0, min(100, value))
        done = await _with_endpoint(lambda ep: ep.SetMasterVolumeLevelScalar(value / 100.0, None) or True)
        if done is None:
            self._media_key(VK_VOLUME_UP if value > 50 else VK_VOLUME_DOWN)

    async def _seek(self, position_ms: int) -> None:
        if position_ms < 0:
            return
        session = await _session()
        if session is not None:
            try:
                await session.try_change_playback_position_async(position_ms * 10_000)
            except Exception:
                log.debug("seek failed", exc_info=True)

    async def full_state(self) -> dict[str, Any]:
        state = await _with_endpoint(
            lambda ep: (max(0, min(100, round(ep.GetMasterVolumeLevelScalar() * 100))), bool(ep.GetMute()))
        )
        volume, muted = state if state is not None else (-1, False)
        base = {"type": "media_control", "action": "media_info", "volume": volume, "is_muted": muted}

        session = await _session()
        if session is not None:
            try:
                from winrt.windows.media.control import (
                    GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status,
                )

                playback = session.get_playback_info()
                has_media = playback is not None
                is_playing = has_media and playback.playback_status == Status.PLAYING
                timeline = session.get_timeline_properties()
                props = await session.try_get_media_properties_async()
                title = props.title or ("Now Playing" if has_media else "No Media Playing")
                return {
                    **base,
                    "title": title,
                    "artist": props.artist or "",
                    "is_playing": is_playing,
                    "has_media": has_media,
                    "position": _ms(timeline.position),
                    "duration": _ms(timeline.end_time),
                }
            except Exception:
                log.debug("media properties unavailable", exc_info=True)

        return {
            **base,
            "title": "No Media Playing",
            "artist": "",
            "is_playing": False,
            "has_media": False,
            "position": 0,
            "duration": 0,
        }

    async def _push_loop(self, session) -> None:
        while session.is_open:
            await session.send_encrypted(await self.full_state())
            await asyncio.sleep(MEDIA_INFO_INTERVAL_SECONDS)
