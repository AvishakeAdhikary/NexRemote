"""One-time import of the WinUI host's JSON files into the database.

The WinUI host (Store 1.0.0.0) stored `settings.json` (PascalCase keys) and
`trusted_devices.json` in the package LocalState folder, which is the same folder this host
uses. Importing keeps the PC's DeviceId and the trusted-device public keys, so phones that
already paired reconnect without pairing again. The certificate files in `certs/` are reused
in place.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nexremote_server.db.engine import SettingsStore, TrustedDeviceStore
from nexremote_server.db.models import AppSettings, TrustedDevice

log = logging.getLogger(__name__)

_THEME = {0: "system", 1: "light", 2: "dark", "system": "system", "light": "light", "dark": "dark"}


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(value, UTC)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _read_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8-sig")
        return json.loads(text) if text.strip() else None
    except (OSError, ValueError):
        log.warning("could not read legacy file %s", path, exc_info=True)
        return None


def _candidate_roots(data_dir: Path) -> list[Path]:
    roots = [data_dir]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        unpackaged = Path(local) / "NexRemote"
        if unpackaged.resolve() != data_dir.resolve():
            roots.append(unpackaged)
    return roots


def settings_from_legacy(raw: dict[str, Any], defaults: AppSettings) -> AppSettings:
    values = defaults.model_dump()
    for key, value in raw.items():
        field = _snake(key)
        if field == "theme_preference":
            value = _THEME.get(value if not isinstance(value, str) else value.lower(), "system")
        if field not in AppSettings.model_fields or value is None:
            continue
        values[field] = value
    for stamp in (
        "terms_of_service_accepted_at",
        "terms_and_conditions_accepted_at",
        "privacy_policy_accepted_at",
    ):
        values[stamp] = (
            _parse_time(values.get(stamp)) if not isinstance(values.get(stamp), datetime) else values[stamp]
        )
    return AppSettings.model_validate(values)


def devices_from_legacy(raw: dict[str, Any]) -> list[TrustedDevice]:
    devices: list[TrustedDevice] = []
    now = datetime.now(UTC)
    for device_id, record in raw.items():
        if not isinstance(record, dict) or not device_id:
            continue
        devices.append(
            TrustedDevice(
                device_id=device_id,
                name=str(record.get("name") or ""),
                public_key=str(record.get("public_key") or ""),
                first_connected=_parse_time(record.get("first_connected")) or now,
                last_connected=_parse_time(record.get("last_connected")) or now,
            )
        )
    return devices


def import_legacy(
    data_dir: Path, settings: SettingsStore, devices: TrustedDeviceStore, fresh_db: bool
) -> bool:
    """Import once into a freshly created DB. Returns True if anything was imported."""
    if not fresh_db:
        return False
    imported = False
    for root in _candidate_roots(data_dir):
        settings_path = root / "settings.json"
        raw_settings = _read_json(settings_path) if settings_path.exists() else None
        if isinstance(raw_settings, dict):
            settings.replace(settings_from_legacy(raw_settings, settings.current))
            _mark_imported(settings_path)
            imported = True
            log.info("imported legacy settings from %s", settings_path)

        devices_path = root / "trusted_devices.json"
        raw_devices = _read_json(devices_path) if devices_path.exists() else None
        if isinstance(raw_devices, dict):
            for device in devices_from_legacy(raw_devices):
                devices.upsert(device)
            _mark_imported(devices_path)
            imported = True
            log.info("imported %d legacy trusted devices from %s", len(raw_devices), devices_path)

        legacy_certs = root / "certs"
        target_certs = data_dir / "certs"
        if (
            root != data_dir
            and (legacy_certs / "server.crt").exists()
            and not (target_certs / "server.crt").exists()
        ):
            target_certs.mkdir(parents=True, exist_ok=True)
            for name in ("server.crt", "server.key"):
                (target_certs / name).write_bytes((legacy_certs / name).read_bytes())
            imported = True
        if imported:
            break
    return imported


def _mark_imported(path: Path) -> None:
    try:
        path.replace(path.with_suffix(path.suffix + ".imported"))
    except OSError:
        log.debug("could not rename %s after import", path, exc_info=True)
