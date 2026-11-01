"""Task manager: processes and system usage."""

from __future__ import annotations

import asyncio
import os
import threading
import time
from typing import Any

import psutil

from nexremote_server.features.base import Feature
from nexremote_server.protocol.jsonutil import get_int, get_str

SNAPSHOT_FRESHNESS_SECONDS = 1.0


def _error(message: str, **extra: Any) -> dict[str, Any]:
    return {"type": "task_manager", "action": "error", "message": message, **extra}


def _process_name(proc: psutil.Process) -> str:
    # .NET Process.ProcessName has no extension; keep the same names on the wire.
    name = proc.info.get("name") or ""
    return name[:-4] if name.lower().endswith(".exe") else name


class TaskManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot: dict[str, Any] | None = None
        self._snapshot_at = 0.0
        self._refreshing = False
        psutil.cpu_percent(interval=None)  # prime the system CPU sampler

    def processes(self) -> list[dict[str, Any]]:
        cpu_count = psutil.cpu_count() or 1
        result = []
        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                cpu = proc.cpu_percent(interval=None) / cpu_count
                mem = proc.info["memory_info"]
                result.append(
                    {
                        "pid": proc.info["pid"],
                        "name": _process_name(proc),
                        "cpu": round(max(0.0, min(100.0, cpu)), 1),
                        "memory": mem.rss if mem else 0,
                    }
                )
            except (psutil.Error, OSError):
                continue
        result.sort(key=lambda p: (-p["cpu"], p["name"].lower()))
        return result

    def system(self) -> dict[str, Any]:
        vm = psutil.virtual_memory()
        disk_percent = 0.0
        try:
            disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
            disk_percent = disk.used * 100.0 / disk.total if disk.total else 0.0
        except OSError:
            pass
        return {
            "cpu_usage": round(psutil.cpu_percent(interval=None), 1),
            "memory_usage": round(float(vm.percent), 1),
            "disk_usage": round(disk_percent, 1),
            "memory_total": vm.total,
            "memory_available": vm.available,
        }

    def _capture_snapshot(self) -> dict[str, Any]:
        return {
            "type": "task_manager",
            "action": "snapshot",
            "system": self.system(),
            "processes": self.processes(),
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            fresh = (
                self._snapshot is not None
                and time.monotonic() - self._snapshot_at < SNAPSHOT_FRESHNESS_SECONDS
            )
            if fresh or (self._snapshot is not None and self._refreshing):
                return self._snapshot  # type: ignore[return-value]
            if self._snapshot is not None:
                # Serve the stale snapshot now and refresh in the background (legacy behaviour).
                self._refreshing = True
                threading.Thread(target=self._refresh, daemon=True).start()
                return self._snapshot
        snap = self._capture_snapshot()
        with self._lock:
            self._snapshot, self._snapshot_at = snap, time.monotonic()
        return snap

    def _refresh(self) -> None:
        try:
            snap = self._capture_snapshot()
            with self._lock:
                self._snapshot, self._snapshot_at = snap, time.monotonic()
        finally:
            self._refreshing = False

    def end_process(self, pid: int) -> dict[str, Any]:
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            name = name[:-4] if name.lower().endswith(".exe") else name
            victims = proc.children(recursive=True) + [proc]
            for victim in victims:
                try:
                    victim.kill()
                except psutil.NoSuchProcess:
                    pass
            psutil.wait_procs(victims, timeout=3)
            return {"type": "task_manager", "action": "process_ended", "pid": pid, "name": name}
        except psutil.NoSuchProcess:
            return _error("Process not found")
        except psutil.AccessDenied:
            return _error("Elevation required", elevation_required=True)
        except Exception as exc:
            return _error(f"Failed to end process: {exc}")

    def handle(self, msg: dict[str, Any]) -> dict[str, Any]:
        action = get_str(msg, "action")
        try:
            match action:
                case "snapshot":
                    return self.snapshot()
                case "list_processes":
                    return {"type": "task_manager", "action": "list_processes", "processes": self.processes()}
                case "end_process":
                    return self.end_process(get_int(msg, "pid"))
                case "system_info":
                    return {"type": "task_manager", "action": "system_info", **self.system()}
                case _:
                    return _error(f"Unknown action: {action}")
        except Exception as exc:
            return _error(str(exc))


class TaskManagerFeature(Feature):
    message_types = ("task_manager",)

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.manager = TaskManager()

    async def handle(self, session, msg_type: str, msg: dict[str, Any]) -> None:
        await session.send_encrypted(await asyncio.to_thread(self.manager.handle, msg))
