"""
Automatic Windows Firewall Configuration.

All firewall operations require admin.  Instead of requiring the entire
application to run elevated, we spawn a short-lived helper script
(`elevated_ops.py`) through UAC using ``elevate.run_elevated()``.
"""
from utils.elevate import is_admin, run_elevated
from utils.logger import get_logger

logger = get_logger(__name__)


def configure_firewall(
    tcp_port: str = "8765",
    udp_port: str = "37020",
) -> dict:
    """
    Configure Windows Firewall to allow NexRemote server traffic.

    Triggers a UAC prompt if the current process is not already elevated.

    Returns
    -------
    dict
        ``{'success': bool, 'message': str, 'detail': str | None}``
    """
    logger.info("Configuring firewall rules (will request UAC if needed)...")

    result = run_elevated(
        "--firewall-add",
        "--tcp-port", tcp_port,
        "--udp-port", udp_port,
    )

    if result["success"]:
        logger.info("Firewall rules configured successfully.")
    else:
        logger.warning(f"Firewall configuration failed: {result['message']}")

    return result


def remove_firewall_rules() -> dict:
    """
    Remove NexRemote firewall rules.  Triggers UAC.
    """
    logger.info("Removing firewall rules (will request UAC if needed)...")
    result = run_elevated("--firewall-remove")

    if result["success"]:
        logger.info("Firewall rules removed.")
    else:
        logger.warning(f"Failed to remove firewall rules: {result['message']}")

    return result