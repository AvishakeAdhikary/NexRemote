"""Local network address helpers."""

from __future__ import annotations

import socket

import psutil


def primary_lan_ip() -> str:
    """The address the OS would route the internet through (no packet is sent)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def all_lan_ips() -> list[dict[str, str]]:
    """IPv4 addresses of interfaces that are up, excluding loopback and link-local."""
    stats = psutil.net_if_stats()
    result: list[dict[str, str]] = []
    for name, addrs in psutil.net_if_addrs().items():
        if name in stats and not stats[name].isup:
            continue
        for addr in addrs:
            if addr.family != socket.AF_INET:
                continue
            if addr.address.startswith(("127.", "169.254.")):
                continue
            result.append({"interface": name, "address": addr.address})
    primary = primary_lan_ip()
    result.sort(key=lambda item: item["address"] != primary)
    return result
