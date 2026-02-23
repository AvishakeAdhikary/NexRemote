"""
Elevated Operations — runs as a SEPARATE process with admin privileges.

This script is launched via ``elevate.run_elevated()`` which triggers a
Windows UAC consent dialog.  It is the ONLY thing that ever runs elevated.

Usage (invoked automatically — not called directly by users):

    python elevated_ops.py --result-file C:\\Temp\\result.json --firewall-add
    python elevated_ops.py --result-file C:\\Temp\\result.json --firewall-remove
    python elevated_ops.py --result-file C:\\Temp\\result.json --kill-pid 1234
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


# ── Firewall helpers ──────────────────────────────────────────────────────────

RULE_NAME = "NexRemote Server"
DEFAULT_TCP_PORT = "8765"
DEFAULT_UDP_PORT = "37020"


def _exe_path() -> str:
    """Best-effort executable path for firewall program rules."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return sys.executable


def firewall_add(
    tcp_port: str = DEFAULT_TCP_PORT,
    udp_port: str = DEFAULT_UDP_PORT,
    profile: str = "private",
) -> dict:
    """
    Add NexRemote TCP + UDP firewall rules.

    Parameters
    ----------
    profile : str
        Which network profiles to apply the rule to.
        One of ``'private'``, ``'public'``, or ``'all'`` (private + public + domain).
    """
    errors = []
    exe = _exe_path()
    # netsh expects 'private', 'public', or 'any'
    netsh_profile = "any" if profile == "all" else profile

    # Remove stale rules first (best-effort).
    subprocess.run(
        ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={RULE_NAME}"],
        capture_output=True,
        check=False,
    )

    # TCP inbound (WebSocket)
    res = subprocess.run(
        [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={RULE_NAME} (TCP)",
            "dir=in", "action=allow", "protocol=TCP",
            f"localport={tcp_port}",
            f"program={exe}",
            f"profile={netsh_profile}",
            "enable=yes",
        ],
        capture_output=True,
    )
    if res.returncode != 0:
        errors.append(f"TCP rule failed: {res.stderr.decode(errors='replace')}")

    # Also add the insecure port (8766) for dual-protocol support
    subprocess.run(
        [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={RULE_NAME} (TCP-Insecure)",
            "dir=in", "action=allow", "protocol=TCP",
            "localport=8766",
            f"program={exe}",
            f"profile={netsh_profile}",
            "enable=yes",
        ],
        capture_output=True,
        check=False,
    )

    # UDP inbound (Discovery)
    res = subprocess.run(
        [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={RULE_NAME} (UDP)",
            "dir=in", "action=allow", "protocol=UDP",
            f"localport={udp_port}",
            f"program={exe}",
            f"profile={netsh_profile}",
            "enable=yes",
        ],
        capture_output=True,
    )
    if res.returncode != 0:
        errors.append(f"UDP rule failed: {res.stderr.decode(errors='replace')}")

    if errors:
        return {"success": False, "message": "; ".join(errors), "detail": None}
    profile_label = {"private": "Private", "public": "Public", "all": "All"}[profile]
    return {"success": True, "message": f"Firewall rules configured for {profile_label} networks.", "detail": None}


def firewall_remove() -> dict:
    """Remove all NexRemote firewall rules."""
    subprocess.run(
        ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={RULE_NAME}"],
        capture_output=True,
        check=False,
    )
    # Also remove the TCP-Insecure variant if it exists
    subprocess.run(
        ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={RULE_NAME} (TCP-Insecure)"],
        capture_output=True,
        check=False,
    )
    return {"success": True, "message": "Firewall rules removed.", "detail": None}


# ── Process kill helper ───────────────────────────────────────────────────────

def kill_pid(pid: int) -> dict:
    """Force-kill a process by PID (elevated)."""
    try:
        import psutil  # noqa: delayed import — may not be on PATH in frozen builds
        proc = psutil.Process(pid)
        name = proc.name()
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except psutil.TimeoutExpired:
            proc.kill()
        return {
            "success": True,
            "message": f"Process '{name}' (PID {pid}) terminated.",
            "detail": None,
        }
    except Exception as e:
        return {"success": False, "message": str(e), "detail": None}


# ── Entry point ───────────────────────────────────────────────────────────────

def _write_result(result_file: str, data: dict):
    """Atomically write result JSON for the calling process to read."""
    p = Path(result_file)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="NexRemote elevated operations")
    parser.add_argument("--result-file", required=True, help="Path to write JSON result")
    parser.add_argument("--firewall-add", action="store_true")
    parser.add_argument("--firewall-remove", action="store_true")
    parser.add_argument("--kill-pid", type=int, default=None)
    parser.add_argument("--tcp-port", default=DEFAULT_TCP_PORT)
    parser.add_argument("--udp-port", default=DEFAULT_UDP_PORT)
    parser.add_argument(
        "--firewall-profile",
        choices=["private", "public", "all"],
        default="private",
        help="Which network profiles to apply firewall rules to.",
    )
    args = parser.parse_args()

    result = {"success": False, "message": "No operation specified.", "detail": None}

    try:
        if args.firewall_add:
            result = firewall_add(
                tcp_port=args.tcp_port,
                udp_port=args.udp_port,
                profile=args.firewall_profile,
            )
        elif args.firewall_remove:
            result = firewall_remove()
        elif args.kill_pid is not None:
            result = kill_pid(args.kill_pid)
    except Exception as e:
        result = {"success": False, "message": str(e), "detail": None}

    _write_result(args.result_file, result)


if __name__ == "__main__":
    main()
