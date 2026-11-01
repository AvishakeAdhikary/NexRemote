"""Database tables and the typed settings model."""

from __future__ import annotations

import socket
import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class Setting(SQLModel, table=True):
    key: str = SQLField(primary_key=True)
    value: str  # JSON-encoded


class TrustedDevice(SQLModel, table=True):
    device_id: str = SQLField(primary_key=True)
    name: str = ""
    public_key: str = ""
    platform: str = ""
    first_connected: datetime = SQLField(default_factory=utcnow)
    last_connected: datetime = SQLField(default_factory=utcnow)


class ConnectionEvent(SQLModel, table=True):
    id: int | None = SQLField(default=None, primary_key=True)
    at: datetime = SQLField(default_factory=utcnow, index=True)
    device_id: str = ""
    device_name: str = ""
    event: str = ""  # connected | disconnected | rejected | auth_failed | approved | denied
    detail: str = ""
    transport: str = ""  # secure | insecure


class AppSettings(BaseModel):
    """User-facing settings. Field names are the persisted keys."""

    pc_name: str = Field(default_factory=socket.gethostname)
    device_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    server_port: int = Field(default=8765, ge=1024, le=65535)
    server_port_insecure: int = Field(default=8766, ge=1024, le=65535)
    discovery_port: int = Field(default=37020, ge=1024, le=65535)
    enable_remote_access: bool = True
    max_clients: int = Field(default=5, ge=0, le=50)
    require_approval: bool = True
    log_level: str = "Information"
    auto_start: bool = False
    minimize_to_tray: bool = True
    show_notifications: bool = True
    theme_preference: Literal["system", "light", "dark"] = "system"

    terms_of_service_accepted: bool = False
    terms_of_service_accepted_at: datetime | None = None
    terms_of_service_version_accepted: str | None = None
    terms_and_conditions_accepted: bool = False
    terms_and_conditions_accepted_at: datetime | None = None
    terms_and_conditions_version_accepted: str | None = None
    privacy_policy_accepted: bool = False
    privacy_policy_accepted_at: datetime | None = None
    privacy_policy_version_accepted: str | None = None

    remote_control_consent_granted: bool = False
    background_consent_granted: bool = False
    camera_access_consent_granted: bool = False
    phone_control_enabled: bool = True

    certificate_thumbprint: str | None = None
    certificate_fingerprint: str | None = None

    def legal_current(self, version: str) -> bool:
        return (
            self.terms_of_service_accepted
            and self.terms_and_conditions_accepted
            and self.privacy_policy_accepted
            and self.terms_of_service_version_accepted == version
            and self.terms_and_conditions_version_accepted == version
            and self.privacy_policy_version_accepted == version
        )


# Keys the control API may change. Identity and certificate stay internal.
USER_EDITABLE_SETTINGS = frozenset(
    {
        "pc_name",
        "server_port",
        "server_port_insecure",
        "discovery_port",
        "enable_remote_access",
        "max_clients",
        "require_approval",
        "log_level",
        "minimize_to_tray",
        "show_notifications",
        "theme_preference",
        "phone_control_enabled",
    }
)
