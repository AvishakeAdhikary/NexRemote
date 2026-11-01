"""Text clipboard get / set / clear."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from nexremote_server.features.base import Feature
from nexremote_server.protocol.jsonutil import get_str

try:
    import win32clipboard
    import win32con
except ImportError:  # pragma: no cover - non-Windows development hosts
    win32clipboard = None  # type: ignore[assignment]
    win32con = None  # type: ignore[assignment]


def _error(message: str) -> dict[str, Any]:
    return {"type": "clipboard", "action": "error", "message": message}


def _open() -> bool:
    # Another app can hold the clipboard briefly; retry a few times before reporting busy.
    for _ in range(5):
        try:
            win32clipboard.OpenClipboard()
            return True
        except Exception:
            time.sleep(0.02)
    return False


def handle_clipboard(msg: dict[str, Any]) -> dict[str, Any]:
    action = get_str(msg, "action").lower()
    if action not in ("get", "set", "clear"):
        return _error(f"Unknown action: {action}")
    if win32clipboard is None:
        return _error("Clipboard is unavailable on this host")
    if not _open():
        return (
            {"type": "clipboard", "action": "content", "text": ""}
            if action == "get"
            else _error("Clipboard is busy")
        )
    try:
        if action == "get":
            try:
                text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            except Exception:
                text = ""
            return {"type": "clipboard", "action": "content", "text": text or ""}
        win32clipboard.EmptyClipboard()
        if action == "clear":
            return {"type": "clipboard", "action": "cleared"}
        value = get_str(msg, "text")
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, value)
        return {"type": "clipboard", "action": "updated", "text": value}
    except Exception as exc:
        return _error(str(exc))
    finally:
        win32clipboard.CloseClipboard()


class ClipboardFeature(Feature):
    message_types = ("clipboard",)

    async def handle(self, session, msg_type: str, msg: dict[str, Any]) -> None:
        await session.send_encrypted(await asyncio.to_thread(handle_clipboard, msg))
