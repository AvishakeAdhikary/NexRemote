"""SQLite engine, schema versioning and the settings / trusted-device stores."""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import event, text
from sqlmodel import Session, SQLModel, create_engine, delete, select

from nexremote_server.db.models import AppSettings, ConnectionEvent, Setting, TrustedDevice, utcnow

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1


def _migrate(engine) -> None:
    """Idempotent, forward-only schema steps. Add a branch per SCHEMA_VERSION bump."""
    with engine.begin() as conn:
        current = conn.execute(text("PRAGMA user_version")).scalar_one()
        if current < 1:
            SQLModel.metadata.create_all(conn)
        conn.execute(text(f"PRAGMA user_version = {SCHEMA_VERSION}"))


def create_db_engine(path: Path | str):
    url = "sqlite://" if str(path) == ":memory:" else f"sqlite:///{Path(path).as_posix()}"
    kwargs: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
    if url == "sqlite://":
        from sqlalchemy.pool import StaticPool

        kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _record) -> None:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()

    _migrate(engine)
    return engine


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


class SettingsStore:
    def __init__(self, engine) -> None:
        self._engine = engine
        self._lock = threading.Lock()
        self._current = self._load()

    def _load(self) -> AppSettings:
        with Session(self._engine) as s:
            rows = {row.key: json.loads(row.value) for row in s.exec(select(Setting))}
        known = {k: v for k, v in rows.items() if k in AppSettings.model_fields}
        settings = AppSettings.model_validate(known)
        if not rows:
            self._write(settings, settings.model_dump(mode="json"))
        return settings

    @property
    def current(self) -> AppSettings:
        return self._current

    def is_empty(self) -> bool:
        with Session(self._engine) as s:
            return s.exec(select(Setting).limit(1)).first() is None

    def update(self, **changes: Any) -> AppSettings:
        with self._lock:
            merged = self._current.model_dump()
            merged.update(changes)
            updated = AppSettings.model_validate(merged)
            dumped = updated.model_dump(mode="json")
            self._write(updated, {k: dumped[k] for k in changes})
            self._current = updated
            return updated

    def replace(self, settings: AppSettings) -> None:
        with self._lock:
            self._write(settings, settings.model_dump(mode="json"))
            self._current = settings

    def _write(self, _settings: AppSettings, values: dict[str, Any]) -> None:
        with Session(self._engine) as s:
            for key, value in values.items():
                s.merge(Setting(key=key, value=json.dumps(value)))
            s.commit()


class TrustedDeviceStore:
    def __init__(self, engine) -> None:
        self._engine = engine

    def get(self, device_id: str) -> TrustedDevice | None:
        with Session(self._engine) as s:
            # Device IDs were compared case-insensitively by the legacy host.
            row = s.get(TrustedDevice, device_id)
            if row is None:
                row = s.exec(select(TrustedDevice).where(TrustedDevice.device_id.ilike(device_id))).first()
            return row

    def all(self) -> list[TrustedDevice]:
        with Session(self._engine) as s:
            return list(s.exec(select(TrustedDevice).order_by(TrustedDevice.last_connected.desc())))

    def record_connection(self, device_id: str, name: str, public_key: str, platform: str = "") -> None:
        now = utcnow()
        with Session(self._engine) as s:
            existing = self.get(device_id)
            if existing is not None:
                existing = s.merge(existing)
                existing.name = name
                existing.last_connected = now
                if public_key:
                    existing.public_key = public_key
                if platform:
                    existing.platform = platform
            else:
                s.add(
                    TrustedDevice(
                        device_id=device_id,
                        name=name,
                        public_key=public_key,
                        platform=platform,
                        first_connected=now,
                        last_connected=now,
                    )
                )
            s.commit()

    def upsert(self, device: TrustedDevice) -> None:
        with Session(self._engine) as s:
            device.first_connected = _as_utc(device.first_connected)
            device.last_connected = _as_utc(device.last_connected)
            s.merge(device)
            s.commit()

    def remove(self, device_id: str) -> bool:
        with Session(self._engine) as s:
            row = self.get(device_id)
            if row is None:
                return False
            s.exec(delete(TrustedDevice).where(TrustedDevice.device_id == row.device_id))
            s.commit()
            return True

    def count(self) -> int:
        return len(self.all())


class EventLog:
    MAX_ROWS = 2000

    def __init__(self, engine) -> None:
        self._engine = engine

    def add(self, **fields: Any) -> None:
        try:
            with Session(self._engine) as s:
                s.add(ConnectionEvent(**fields))
                s.commit()
                total = s.exec(text("SELECT COUNT(*) FROM connectionevent")).scalar_one()
                if total > self.MAX_ROWS:
                    s.exec(
                        text(
                            "DELETE FROM connectionevent WHERE id IN "
                            "(SELECT id FROM connectionevent ORDER BY id ASC LIMIT :n)"
                        ).bindparams(n=total - self.MAX_ROWS)
                    )
                    s.commit()
        except Exception:  # an audit trail must never break a connection
            log.debug("failed to record connection event", exc_info=True)

    def recent(self, limit: int = 100) -> list[ConnectionEvent]:
        with Session(self._engine) as s:
            return list(s.exec(select(ConnectionEvent).order_by(ConnectionEvent.id.desc()).limit(limit)))
