# AGENTS.md

Scope: the whole NexRemote monorepo. Project folders have their own `AGENTS.md` with more detail; the closest file to what you are editing wins when they disagree.

## What NexRemote is

A free, ad-free remote-control product with two parts that talk over the local network (or USB via `adb reverse`):

- **Windows host** (`windows_app/`): runs a WebSocket server on the PC and executes input, streaming, file, task, media and clipboard commands. Published on the Microsoft Store.
- **Android client** (`client/`): discovers the PC, pairs with it, and drives it. Also streams the phone's own screen to the PC and can accept remote-control input from the PC.

No accounts, no cloud relay, no telemetry, no ads. Everything stays between the user's own phone and PC.

## Repository map

| Path | What lives there |
|---|---|
| `windows_app/server/` | Python backend (astral-uv project, FastAPI, SQLite via SQLModel). The protocol server, discovery, features, local control API. |
| `windows_app/desktop/` | Electron shell + Next.js (static export) UI. Spawns and supervises the Python sidecar, tray, MSIX packaging. |
| `windows_app/NexRemote/` | Legacy WinUI 3/.NET host. Protocol reference only until the rebuild passes the parity checklist, then deleted (git history keeps it). |
| `client/NexRemote/` | Android app (Kotlin, Jetpack Compose, Gradle). |
| `docs/legal/` | Privacy policy, terms, store submission notes. |
| `scripts/` | `build.ps1` (build + signing), `dev.ps1`. |
| `shared/` | Logos. `protocol.proto` is obsolete and unused. |
| `.github/workflows/ci.yml` | CI builds and edge releases. |

## Wire contract (single source of truth)

Both sides must agree on all of this. Phones already in users' hands run the v1 client, and the Store build of the host is v1, so **v1 behaviour must keep working byte-for-byte**.

### Discovery and connection

- **Discovery:** the client sends a UDP datagram starting with ASCII `NEXREMOTE_DISCOVER` to broadcast port `37020`. The host replies by unicast with `{"type":"discovery_response","name","port":8765,"port_insecure":8766,"id","version","cert_fingerprint"}`. There is no `host` field: the client uses the packet's source address.
- **QR payload:** `{"host","port","port_insecure","name","id","cert_fingerprint"}`.
- **Ports:** `8765` is `wss://` with a self-signed RSA cert, pinned by SHA-256 fingerprint (uppercase hex pairs joined by `:`). `8766` is plain `ws://`, used for the LAN fallback and for USB.
- **Framing:** text frames carry JSON. Binary frames carry streams. Any path upgrades to a WebSocket, and `GET /` returns `NexRemote`.

### Auth

1. **Client → host:** plaintext `auth` with `{device_id, device_name, client_public_key (Base64 SPKI, EC P-256), client_version, platform}`.
2. **Secure port only:** the host sends `auth_challenge` with `{nonce (Base64, 32 bytes), server_name, capabilities, feature_status}`. The client replies `auth_response {device_id, signature}`, an ECDSA-SHA256 signature over the raw nonce bytes. The host accepts DER or raw r‖s.
3. **Approval:** an untrusted device needs approval on the PC (12 s timeout).
4. **Outcome:** `auth_success {server_name, capabilities, feature_status}`, or `auth_failed`, or `connection_rejected`.
5. **Keep-alive:** `ping` is answered with `pong`.

### Encryption

- **Legacy v1:** after auth, JSON is AES-256-CBC with the fixed key `nexremote_encryption_key_32chars`, a zero IV and PKCS7 padding, sent as Base64 text.
  - The receiver first tries to parse plain JSON, then falls back to decrypting.
  - The host always sends `auth_*`, `connection_rejected` and `pong` in plaintext.
- **v2 (negotiated):**
  - The client adds `protocol_version: 2` and `client_ephemeral_key` (Base64 SPKI P-256) to `auth`.
  - A v2 host adds `server_ephemeral_key` and `session_crypto: "aes-256-gcm"` to `auth_success`.
  - Both sides then derive keys with ECDH followed by HKDF-SHA256, one key per direction, and use AES-GCM with counter nonces for all post-auth JSON.
  - If either side lacks the v2 fields, both stay on legacy. The exact derivation lives in `windows_app/server/src/nexremote_server/protocol/v2_crypto.py` and its Kotlin twin. Change them together.

### Commands, binary frames and status

- **Command types** (field `type`, plus `action` / `input_action`):
  - `keyboard`, `mouse`, `macro`
  - `gamepad`, `gamepad_xinput`, `gamepad_dinput`, `gamepad_android`, `gamepad_mode`
  - `camera`, `screen_share`, `file_explorer`, `task_manager`, `media_control`, `clipboard`
  - `phone_screen` (new)
- **Binary frames:** a 4-byte ASCII tag, then a 1-byte stream index, then the payload. Binary frames are never encrypted at the app layer.

  | Tag | Direction | Payload |
  |---|---|---|
  | `SCRN` | host → client | JPEG PC screen frame |
  | `CAMF` | host → client | JPEG PC camera frame |
  | `AUDF` | host → client | PCM16 LE PC audio |
  | `PSCR` | client → host | flags byte (bit0 codec config, bit1 keyframe), then 8-byte big-endian pts in µs, then an H.264 Annex-B access unit |
  | `PAUD` | client → host (1.2) | 8-byte big-endian pts in µs, then PCM16 LE interleaved (rate/channels from `audio_changed`; 48 kHz stereo from Android) |

- **`phone_screen` messages (v1.1):**
  - Client → host: `start` / `config_changed` with `{codec, width, height, fps, rotation, control_available}`, `control_changed {control_available}`, and `stop`.
  - Host → client: `input {input_action: tap|long_press|swipe|key, normalized_x, normalized_y, end_x, end_y, duration_ms, key: back|home|recents}`, `request_keyframe`, and `stop_request`.
  - The host only sends `input` when the phone reported `control_available` and the PC setting `phone_control_enabled` is on.
- **Phone audio (v1.2, additive):**
  - The phone adds `audio_available` to `start` / `config_changed`.
  - Host → phone: `audio_request {enabled}`, sent only when the PC user turns audio on for that phone.
  - The phone replies with `audio_changed {audio_active, audio_available, sample_rate, channels}` and streams `PAUD` while active.
  - Android captures playback audio only (AudioPlaybackCapture), never the microphone, and only when the user turned on "Let the PC hear this phone".
- **Other v1.2 additions:**
  - Capabilities `precise_scroll` and `phone_audio`.
  - `mouse` `scroll` accepts `precise: true`, meaning dx/dy are raw wheel units (120 = one notch) for smooth scrolling. Clients send it only when `precise_scroll` is advertised.
  - `task_manager` system info adds `disk_active` (Task Manager's disk active time), `disk_read_bps`, `disk_write_bps`, `net_sent_bps`, `net_recv_bps`, `cpu_count`, `cpu_freq_mhz` and `process_count`. `disk_usage` keeps meaning space used.
  - The process list excludes PID 0, and `memory` is the private working set.
- **Status objects:** `capabilities` and `feature_status` (`{supported, available, reason, action_required}` per feature) drive the client's home screen. Add keys freely; never rename or remove them.
- **Wire names** are snake_case. Keep them stable even when the language-side names differ.

### Rules for protocol changes

- Changes must be **additive** and land in the host and the client in the same change.
- Each change needs golden tests in `windows_app/server/tests/` and client unit tests.
- Update this section when the contract changes.

## Release identities (never change these)

- **Microsoft Store:**
  - Package identity `NeuralNexusStudios.NexRemote`, publisher `CN=8559855F-6955-4418-A6D8-835C3238CF34`, publisher display name `Neural Nexus Studios`.
  - Versions are `Major.Minor.Build.0`; the Store requires the last field to be 0.
  - Changing identity or publisher would turn the update into a different app and lose existing users' data.
- **Google Play:** `applicationId` `com.neuralnexusstudios.nex_remote`.
  - `versionCode` must increase on every upload.
  - Keystores come from env vars or CI secrets (see `scripts/build.ps1`), or, for local builds, the git-ignored `client/NexRemote/keystore.properties`. Never commit keystores or their passwords.
  - The upload key was replaced in November 2026 (the old password was lost). If Play rejects a bundle with an upload-key mismatch, request an upload key reset with the new key's certificate (`dist/store-assets/upload_certificate.pem`, re-exportable with `keytool -export -rfc`).
- **Version bumps:** bump Windows and Android together when a release adds protocol features.

## Ground rules

- **Product:** no telemetry, analytics, ads, accounts or cloud services.
- **Repository hygiene:** don't commit secrets, keystores, `.pfx` files, signing passwords or tester data.
- **Store honesty:** never fake testers, installs, reviews or feedback, and never make a store attestation that isn't true. The Play closed-testing rule (12+ real opted-in testers for 14 days) must be met by real people.
- **Agent notes:** private notes go in the gitignored per-agent folders (`.claude/`, `.gemini/`, `.codex/`, and so on) at the root or inside a project. Play production Q&A drafts live in `client/.gemini/CLIENT-PRODUCTION-QA.md`.
- **Keep AGENTS.md current:** when you change structure, commands or the contract, update the affected `AGENTS.md` files in the same change.

## Quick commands

| Area | Command (run from) |
|---|---|
| Server tests | `uv run pytest` (`windows_app/server/`) |
| Server dev run | `uv run nexremote-server --dev` (`windows_app/server/`) |
| Desktop dev | `npm run dev` (`windows_app/desktop/`) |
| Desktop package (MSIX) | `npm run package:appx` (`windows_app/desktop/`) |
| Android tests | `.\gradlew.bat :app:testDebugUnitTest` (`client/NexRemote/`) |
| Android release | `.\gradlew.bat :app:bundleRelease` (`client/NexRemote/`) |
| Full build | `.\scripts\build.ps1` (repo root) |
