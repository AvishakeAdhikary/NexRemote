"""Fast process sampling on Windows: one NtQuerySystemInformation call for every process.

psutil opens each process separately (~1 s for ~250 processes, with access-denied fallbacks).
SystemProcessInformation returns names, CPU times and the private working set (the "Memory"
column in Windows Task Manager) for all processes in a single syscall, in a few milliseconds.
"""

from __future__ import annotations

import ctypes
import struct
import sys
from dataclasses import dataclass

STATUS_INFO_LENGTH_MISMATCH = 0xC0000004
SYSTEM_PROCESS_INFORMATION = 5

# SYSTEM_PROCESS_INFORMATION field offsets (64-bit Windows).
_OFF_NEXT = 0
_OFF_PRIVATE_WS = 8
_OFF_USER_TIME = 40
_OFF_KERNEL_TIME = 48
_OFF_NAME_LEN = 56
_OFF_NAME_PTR = 64
_OFF_PID = 80
_OFF_WORKING_SET = 144


@dataclass(slots=True)
class ProcSample:
    pid: int
    name: str
    cpu_time_100ns: int
    private_working_set: int
    working_set: int


def available() -> bool:
    return sys.platform == "win32" and struct.calcsize("P") == 8


def sample() -> list[ProcSample]:
    """All processes, or raises OSError if the query fails."""
    ntdll = ctypes.WinDLL("ntdll")
    query = ntdll.NtQuerySystemInformation
    query.restype = ctypes.c_ulong
    query.argtypes = (ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong))

    size = 512 * 1024
    for _ in range(8):
        buf = ctypes.create_string_buffer(size)
        needed = ctypes.c_ulong(0)
        status = query(SYSTEM_PROCESS_INFORMATION, buf, size, ctypes.byref(needed))
        if status == STATUS_INFO_LENGTH_MISMATCH:
            size = max(size * 2, needed.value + 64 * 1024)
            continue
        if status != 0:
            raise OSError(f"NtQuerySystemInformation failed: 0x{status:08X}")
        break
    else:
        raise OSError("NtQuerySystemInformation: buffer kept growing")

    raw = buf.raw
    base = ctypes.addressof(buf)
    result: list[ProcSample] = []
    offset = 0
    while True:
        next_offset = struct.unpack_from("<I", raw, offset + _OFF_NEXT)[0]
        private_ws = struct.unpack_from("<q", raw, offset + _OFF_PRIVATE_WS)[0]
        user, kernel = struct.unpack_from("<qq", raw, offset + _OFF_USER_TIME)
        name_len = struct.unpack_from("<H", raw, offset + _OFF_NAME_LEN)[0]
        name_ptr = struct.unpack_from("<Q", raw, offset + _OFF_NAME_PTR)[0]
        pid = struct.unpack_from("<Q", raw, offset + _OFF_PID)[0]
        working_set = struct.unpack_from("<Q", raw, offset + _OFF_WORKING_SET)[0]
        if name_ptr and name_len:
            start = name_ptr - base
            name = raw[start : start + name_len].decode("utf-16-le", errors="replace")
        else:
            name = "System Idle Process" if pid == 0 else ""
        result.append(ProcSample(pid, name, user + kernel, max(0, private_ws), working_set))
        if next_offset == 0:
            break
        offset += next_offset
    return result


class DiskActivity:
    """Disk active time like Windows Task Manager: 100 - PhysicalDisk(_Total) "% Idle Time" (PDH).

    psutil's read_time/write_time are frozen on many Windows systems (e.g. NVMe without diskperf),
    which made "disk active" read 0 % under heavy load. PDH rate counters need two collections, so
    the query stays open and each read() returns the activity since the previous call.
    """

    PDH_FMT_DOUBLE = 0x00000200

    class _Value(ctypes.Structure):
        _fields_ = [("CStatus", ctypes.c_ulong), ("doubleValue", ctypes.c_double)]

    def __init__(self) -> None:
        self._pdh = ctypes.WinDLL("pdh")
        self._query = ctypes.c_void_p()
        self._counter = ctypes.c_void_p()
        if self._pdh.PdhOpenQueryW(None, None, ctypes.byref(self._query)) != 0:
            raise OSError("PdhOpenQuery failed")
        status = self._pdh.PdhAddEnglishCounterW(
            self._query, r"\PhysicalDisk(_Total)\% Idle Time", None, ctypes.byref(self._counter)
        )
        if status != 0:
            self._pdh.PdhCloseQuery(self._query)
            raise OSError(f"PdhAddEnglishCounter failed: 0x{status & 0xFFFFFFFF:08X}")
        self._pdh.PdhCollectQueryData(self._query)

    def read(self) -> float | None:
        if self._pdh.PdhCollectQueryData(self._query) != 0:
            return None
        value = self._Value()
        status = self._pdh.PdhGetFormattedCounterValue(
            self._counter, self.PDH_FMT_DOUBLE, None, ctypes.byref(value)
        )
        if status != 0:
            return None
        return max(0.0, min(100.0, 100.0 - value.doubleValue))
