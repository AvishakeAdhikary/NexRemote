"""Pending connection approvals, answered from the desktop UI."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

from nexremote_server.core.events import EventBus


@dataclass
class PendingApproval:
    device_id: str
    device_name: str
    platform: str
    remote_address: str
    timeout_seconds: float
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    future: asyncio.Future[bool] = field(default_factory=lambda: asyncio.get_running_loop().create_future())

    def describe(self) -> dict[str, object]:
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "platform": self.platform,
            "remote_address": self.remote_address,
            "timeout_seconds": self.timeout_seconds,
            "requested_at": self.requested_at.isoformat(),
        }


class ApprovalService:
    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._pending: dict[str, PendingApproval] = {}

    def pending(self) -> list[dict[str, object]]:
        return [p.describe() for p in self._pending.values()]

    async def request(
        self, device_id: str, device_name: str, platform: str, remote_address: str, timeout: float
    ) -> bool:
        key = device_id.lower()
        approval = self._pending.get(key)
        if approval is None:
            approval = PendingApproval(device_id, device_name, platform, remote_address, timeout)
            self._pending[key] = approval
            self._bus.publish("approval_requested", approval.describe())
        try:
            return await asyncio.wait_for(asyncio.shield(approval.future), timeout)
        except TimeoutError:
            return False
        finally:
            if self._pending.get(key) is approval:
                del self._pending[key]
                self._bus.publish("approval_resolved", {"device_id": device_id})

    def complete(self, device_id: str, approved: bool) -> bool:
        approval = self._pending.pop(device_id.lower(), None)
        if approval is None:
            return False
        if not approval.future.done():
            approval.future.set_result(approved)
        self._bus.publish("approval_resolved", {"device_id": device_id, "approved": approved})
        return True
