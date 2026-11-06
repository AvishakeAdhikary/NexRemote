"""Task manager: processes and system usage."""

from __future__ import annotations

import asyncio
import os
import threading
import time
from typing import Any

import psutil

from nexremote_server.features import winproc
from nexremote_server.features.base import Feature
from nexremote_server.protocol.jsonutil import get_int, get_str

SNAPSHOT_FRESHNESS_SECONDS = 1.0
# PID 0 ("System Idle Process") reports idle time as CPU use; it is not a real workload.
EXCLUDED_PIDS = {0}


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
        self._io_lock = threading.Lock()
        self._last_io: tuple[float, Any, Any] | None = None
        self._fast = winproc.available()
        self._disk_activity: winproc.DiskActivity | None = None
        if winproc.available():
            try:
                self._disk_activity = winproc.DiskActivity()
            except OSError:
                self._disk_activity = None
        self._last_cpu: dict[int, int] = {}
        self._last_cpu_at = 0.0
        psutil.cpu_percent(interval=None)  # prime the system CPU sampler
        self._io_rates()  # prime disk/network rate sampling
        # Prime per-process CPU counters so the first snapshot isn't all zeros.
        self.processes()

    def processes(self) -> list[dict[str, Any]]:
        if self._fast:
            try:
                return self._processes_fast()
            except OSError:
                self._fast = False
        return self._processes_psutil()

    def _processes_fast(self) -> list[dict[str, Any]]:
        now = time.monotonic()
        samples = winproc.sample()
        cpu_count = psutil.cpu_count() or 1
        elapsed_100ns = (now - self._last_cpu_at) * 1e7 * cpu_count if self._last_cpu_at else 0.0
        last = self._last_cpu
        current: dict[int, int] = {}
        result = []
        for proc in samples:
            current[proc.pid] = proc.cpu_time_100ns
            if proc.pid in EXCLUDED_PIDS:
                continue
            previous = last.get(proc.pid)
            cpu = 0.0
            if elapsed_100ns > 0 and previous is not None:
                cpu = (proc.cpu_time_100ns - previous) * 100.0 / elapsed_100ns
            name = proc.name[:-4] if proc.name.lower().endswith(".exe") else proc.name
            result.append(
                {
                    "pid": proc.pid,
                    "name": name,
                    "cpu": round(max(0.0, min(100.0, cpu)), 1),
                    # Private working set: the "Memory" column of Windows Task Manager.
                    "memory": proc.private_working_set or proc.working_set,
                }
            )
        self._last_cpu, self._last_cpu_at = current, now
        result.sort(key=lambda p: (-p["cpu"], -p["memory"], p["name"].lower()))
        return result

    def _processes_psutil(self) -> list[dict[str, Any]]:
        cpu_count = psutil.cpu_count() or 1
        result = []
        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            if proc.info["pid"] in EXCLUDED_PIDS:
                continue
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

    def _io_rates(self) -> dict[str, float]:
        """Disk active time and network throughput since the previous call (like Windows Task Manager)."""
        now = time.monotonic()
        try:
            disk = psutil.disk_io_counters()
        except Exception:
            disk = None
        try:
            net = psutil.net_io_counters()
        except Exception:
            net = None
        with self._io_lock:
            last, self._last_io = self._last_io, (now, disk, net)
        rates = {"disk_active": 0.0, "disk_read_bps": 0.0, "disk_write_bps": 0.0, "net_sent_bps": 0.0, "net_recv_bps": 0.0}
        if last is None:
            return rates
        then, last_disk, last_net = last
        elapsed = max(1e-3, now - then)
        if disk is not None and last_disk is not None:
            busy_ms = getattr(disk, "busy_time", None)
            last_busy = getattr(last_disk, "busy_time", None)
            if busy_ms is not None and last_busy is not None:
                busy = busy_ms - last_busy
            else:  # Windows: no busy_time; read+write time approximates active time
                busy = (disk.read_time + disk.write_time) - (last_disk.read_time + last_disk.write_time)
            rates["disk_active"] = round(max(0.0, min(100.0, busy / (elapsed * 1000.0) * 100.0)), 1)
        if self._disk_activity is not None:
            active = self._disk_activity.read()
            if active is not None:
                rates["disk_active"] = round(active, 1)
            rates["disk_read_bps"] = max(0.0, (disk.read_bytes - last_disk.read_bytes) / elapsed)
            rates["disk_write_bps"] = max(0.0, (disk.write_bytes - last_disk.write_bytes) / elapsed)
        if net is not None and last_net is not None:
            rates["net_sent_bps"] = max(0.0, (net.bytes_sent - last_net.bytes_sent) / elapsed)
            rates["net_recv_bps"] = max(0.0, (net.bytes_recv - last_net.bytes_recv) / elapsed)
        return rates

    def system(self) -> dict[str, Any]:
        vm = psutil.virtual_memory()
        disk_percent = 0.0
        try:
            disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
            disk_percent = disk.used * 100.0 / disk.total if disk.total else 0.0
        except OSError:
            pass
        try:
            freq = psutil.cpu_freq()
        except Exception:
            freq = None
        return {
            "cpu_usage": round(psutil.cpu_percent(interval=None), 1),
            "memory_usage": round(float(vm.percent), 1),
            # Space used on the system drive (kept for 1.0/1.1 clients; newer ones show disk_active).
            "disk_usage": round(disk_percent, 1),
            "memory_total": vm.total,
            "memory_available": vm.available,
            "cpu_count": psutil.cpu_count() or 1,
            "cpu_freq_mhz": round(freq.current) if freq else 0,
            **self._io_rates(),
        }

    def _capture_snapshot(self) -> dict[str, Any]:
        processes = self.processes()
        return {
            "type": "task_manager",
            "action": "snapshot",
            "system": {**self.system(), "process_count": len(processes)},
            "processes": processes,
        }

    def snapshot(self) -> dict[str, Any]:
        if self._fast:
            # ~10 ms with the native sampler: always answer with fresh data (no stale-then-refresh lag).
            with self._lock:
                if self._snapshot is not None and time.monotonic() - self._snapshot_at < 0.5:
                    return self._snapshot
                snap = self._capture_snapshot()
                self._snapshot, self._snapshot_at = snap, time.monotonic()
                return snap
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
