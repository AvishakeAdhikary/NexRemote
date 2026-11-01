"""Wire constants shared with the Android client. Never change existing values."""

PROTOCOL_VERSION = "1.0.0"  # reported in discovery; v1 clients compare against it
NEGOTIATED_PROTOCOL_VERSION = 2

DISCOVERY_MAGIC = b"NEXREMOTE_DISCOVER"
DEFAULT_SECURE_PORT = 8765
DEFAULT_INSECURE_PORT = 8766
DEFAULT_DISCOVERY_PORT = 37020

AUTH_TIMEOUT_SECONDS = 30
AUTH_RESPONSE_TIMEOUT_SECONDS = 15
APPROVAL_TIMEOUT_SECONDS = 12

AUTH = "auth"
AUTH_CHALLENGE = "auth_challenge"
AUTH_RESPONSE = "auth_response"
AUTH_SUCCESS = "auth_success"
AUTH_FAILED = "auth_failed"
CONNECTION_REJECTED = "connection_rejected"
PING = "ping"
PONG = "pong"

SCREEN_FRAME = b"SCRN"
CAMERA_FRAME = b"CAMF"
SCREEN_AUDIO_FRAME = b"AUDF"
PHONE_SCREEN_FRAME = b"PSCR"

LEGAL_DOCUMENT_VERSION = "2026-11-01"  # bump whenever a bundled legal document changes
