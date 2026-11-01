"""System audio loopback capture (WASAPI) as interleaved 16-bit little-endian PCM."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)

CHUNK_FRAMES = 960  # 20 ms at 48 kHz


def _loopback_device(pa) -> dict[str, Any] | None:
    import pyaudiowpatch as pyaudio

    try:
        wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError:
        return None
    speakers = pa.get_device_info_by_index(wasapi["defaultOutputDevice"])
    if speakers.get("isLoopbackDevice"):
        return speakers
    for loopback in pa.get_loopback_device_info_generator():
        if speakers["name"] in loopback["name"]:
            return loopback
    return None


def audio_availability() -> tuple[bool, str]:
    try:
        import pyaudiowpatch as pyaudio
    except ImportError as exc:
        return False, f"audio backend missing ({exc})"
    pa = pyaudio.PyAudio()
    try:
        device = _loopback_device(pa)
        return (True, "") if device is not None else (False, "no default playback device")
    except Exception as exc:
        return False, str(exc)
    finally:
        pa.terminate()


class AudioCapture:
    def __init__(self, on_chunk: Callable[[bytes], None], on_error: Callable[[str, str], None]) -> None:
        self._on_chunk = on_chunk
        self._on_error = on_error
        self._pa = None
        self._stream = None
        self._lock = threading.Lock()

    def start(self) -> tuple[bool, dict[str, Any] | None, str | None, str | None]:
        """Returns (started, format, error_code, error_message)."""
        try:
            import pyaudiowpatch as pyaudio
        except ImportError as exc:
            return False, None, "audio_start_failed", f"System audio capture could not start: {exc}"
        with self._lock:
            if self._stream is not None:
                return False, None, "audio_start_failed", "System audio capture is already running."
            try:
                self._pa = pyaudio.PyAudio()
                device = _loopback_device(self._pa)
                if device is None:
                    raise RuntimeError("no default playback device")
                channels = max(1, min(2, int(device["maxInputChannels"])))
                rate = int(device["defaultSampleRate"])

                def callback(in_data, _frames, _time_info, status):
                    if in_data:
                        try:
                            self._on_chunk(bytes(in_data))
                        except Exception:
                            log.debug("audio chunk delivery failed", exc_info=True)
                    return None, pyaudio.paContinue

                self._stream = self._pa.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=rate,
                    input=True,
                    input_device_index=device["index"],
                    frames_per_buffer=CHUNK_FRAMES,
                    stream_callback=callback,
                )
                self._stream.start_stream()
            except Exception as exc:
                self._cleanup()
                return False, None, "audio_start_failed", f"System audio capture could not start: {exc}"
        fmt = {"sample_rate": rate, "channels": channels, "encoding": "pcm16", "bytes_per_sample": 2}
        return True, fmt, None, None

    def _cleanup(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None

    def stop(self) -> None:
        with self._lock:
            self._cleanup()
