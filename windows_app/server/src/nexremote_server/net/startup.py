"""'Start with Windows' through the MSIX StartupTask declared in the AppxManifest.

The sidecar runs inside the package (it inherits the Electron app's package identity), so
WinRT StartupTask works here. Outside a package (development) it reports unsupported.
"""

from __future__ import annotations

import logging
from typing import Any

from nexremote_server.config import current_package_family_name

log = logging.getLogger(__name__)

TASK_ID = "NexRemoteStartup"
_STATES = {
    0: "disabled",
    1: "disabled_by_user",
    2: "enabled",
    3: "disabled_by_policy",
    4: "enabled_by_policy",
}


async def _task():
    if current_package_family_name() is None:
        return None
    try:
        from winrt.windows.applicationmodel import StartupTask

        return await StartupTask.get_async(TASK_ID)
    except Exception:
        log.debug("StartupTask unavailable", exc_info=True)
        return None


def _describe(task) -> dict[str, Any]:
    if task is None:
        return {"supported": False, "enabled": False, "state": "unsupported"}
    state = _STATES.get(int(task.state), str(task.state))
    return {"supported": True, "enabled": state in ("enabled", "enabled_by_policy"), "state": state}


async def get_startup() -> dict[str, Any]:
    return _describe(await _task())


async def set_startup(enabled: bool) -> dict[str, Any]:
    task = await _task()
    if task is None:
        return _describe(None)
    try:
        if enabled:
            # Shows nothing if already allowed; if the user disabled it in Task Manager the
            # state stays disabled_by_user and only the user can re-enable it there.
            await task.request_enable_async()
        else:
            task.disable()
    except Exception:
        log.warning("changing StartupTask failed", exc_info=True)
    return _describe(await _task())
