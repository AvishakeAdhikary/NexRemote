"""Feature plug-in interface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nexremote_server.core.context import AppContext
    from nexremote_server.core.session import ClientSession


def available(reason: str) -> dict[str, Any]:
    return {"supported": True, "available": True, "reason": reason, "action_required": ""}


def unavailable(reason: str, action_required: str) -> dict[str, Any]:
    return {"supported": True, "available": False, "reason": reason, "action_required": action_required}


class Feature:
    """One protocol feature. Handlers run on the event loop and must not block."""

    #: protocol `type` values routed to this feature (lower-case)
    message_types: tuple[str, ...] = ()

    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx

    async def handle(self, session: ClientSession, msg_type: str, msg: dict[str, Any]) -> None:
        raise NotImplementedError

    async def handle_binary(self, session: ClientSession, tag: bytes, data: bytes) -> bool:
        """Return True if this feature consumed the binary frame."""
        return False

    async def on_session_closed(self, session: ClientSession) -> None:
        return None

    async def start(self) -> None:
        """Start host-wide background work (called when the protocol server starts)."""
        return None

    async def stop(self) -> None:
        return None
