"""Binary stream frames: 4-byte ASCII tag, 1-byte stream index, payload."""

from __future__ import annotations

import struct
from dataclasses import dataclass

from nexremote_server.protocol.constants import PHONE_SCREEN_FRAME

PSCR_FLAG_CONFIG = 0x01
PSCR_FLAG_KEYFRAME = 0x02
_PSCR_HEADER = struct.Struct(">Bq")  # flags, pts in microseconds


def build_frame(tag: bytes, index: int, payload: bytes) -> bytes:
    if len(tag) != 4:
        raise ValueError("frame tag must be 4 bytes")
    return tag + bytes([index & 0xFF]) + payload


def parse_frame(data: bytes) -> tuple[bytes, int, bytes] | None:
    if len(data) < 5:
        return None
    return bytes(data[:4]), data[4], bytes(data[5:])


@dataclass(frozen=True, slots=True)
class PhoneScreenPacket:
    index: int
    flags: int
    pts_us: int
    data: bytes

    @property
    def is_config(self) -> bool:
        return bool(self.flags & PSCR_FLAG_CONFIG)

    @property
    def is_keyframe(self) -> bool:
        return bool(self.flags & PSCR_FLAG_KEYFRAME)


def parse_phone_screen(data: bytes) -> PhoneScreenPacket | None:
    parsed = parse_frame(data)
    if parsed is None:
        return None
    tag, index, payload = parsed
    if tag != PHONE_SCREEN_FRAME or len(payload) < _PSCR_HEADER.size:
        return None
    flags, pts = _PSCR_HEADER.unpack_from(payload)
    return PhoneScreenPacket(index=index, flags=flags, pts_us=pts, data=payload[_PSCR_HEADER.size :])


def build_phone_screen(index: int, flags: int, pts_us: int, data: bytes) -> bytes:
    return build_frame(PHONE_SCREEN_FRAME, index, _PSCR_HEADER.pack(flags & 0xFF, pts_us) + data)
