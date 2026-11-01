# AGENTS.md

Scope: the Windows host workspace under `windows_app/`. The wire contract is defined in the root `AGENTS.md`; it is not repeated here.

## Mission

The Windows app is the NexRemote PC host. It is published on the Microsoft Store as `NeuralNexusStudios.NexRemote`.

It is being rebuilt from WinUI 3/.NET to:

- **Frontend:** Electron with a Next.js UI.
- **Backend:** Python, managed with astral-uv, built on FastAPI, with SQLite.

The rebuild must:

- Ship as a normal Store update (1.0.0.0 → 1.1.0.0) under the **same package identity and publisher**.
- Keep every existing feature.
- Keep working with Android clients already in users' hands (protocol v1, byte-for-byte).
- Carry over each user's settings, server certificate and trusted devices, so paired phones don't have to pair again.

## Layout

```
windows_app/
  server/                    Python backend (uv project)
    pyproject.toml, uv.lock
    src/nexremote_server/
      main.py                entry point: starts all listeners in one asyncio loop
      config.py              paths (MSIX LocalState vs %LOCALAPPDATA%\NexRemote), CLI args
      protocol/              constants, legacy_crypto, v2_crypto, frames, json helpers
      core/                  session, auth, router, state, approvals, event bus
      features/              input, gamepad, screen, audio, camera, files, tasks, media,
                             clipboard, adb, phone_screen
      db/                    SQLModel models, engine, legacy JSON importer
      api/                   local control API for the Electron UI (REST + /events WS)
      net/                   discovery (UDP 37020), certificates, LAN address
    tests/                   pytest: golden protocol tests, auth flows, feature replies
    nexremote-server.spec    PyInstaller onedir spec
  desktop/                   Electron + Next.js
    electron/                main.ts, preload.ts, sidecar.ts, tray.ts
    src/app/                 Next.js App Router pages (static export)
    build/appx/              AppxManifest template + Store assets
    electron-builder.yml
  NexRemote/                 LEGACY WinUI host. Read-only reference; delete once the parity checklist passes.
```

## How it runs

1. Electron starts.
   - It takes the single-instance lock and picks a free port on `127.0.0.1`.
   - It generates a random bearer token.
   - It spawns `nexremote-server.exe` (dev mode: `uv run nexremote-server`) with `--control-port` and `--control-token`.
2. The sidecar starts four listeners in one asyncio loop:

   | Listener | Purpose |
   |---|---|
   | `wss://0.0.0.0:8765` | uvicorn with TLS (`certs/server.crt` and `certs/server.key`) |
   | `ws://0.0.0.0:8766` | uvicorn, plain |
   | UDP `0.0.0.0:37020` | discovery |
   | `http://127.0.0.1:<control-port>` | control API |

3. The renderer only talks to the control API: REST for state and settings, plus a WebSocket at `/events` for approvals, sessions, feature status and the phone-screen video relay. The renderer gets the base URL and token through `preload.ts` (`contextIsolation` on, `nodeIntegration` off).
4. Electron supervises the sidecar: a health check on `GET /health`, a restart with backoff if it crashes, and a clean stop on quit.

**Gating:** the protocol servers only accept connections once the user has accepted the current legal documents (version `2026-11-01`) and granted remote-networking consent. `EnableRemoteAccess` must also be true. These are the same conditions as the legacy app.

## Data and the database

- **Data folder:**
  - Packaged (MSIX): `%LOCALAPPDATA%\Packages\<PackageFamilyName>\LocalState`, the same folder the WinUI app used.
  - Unpackaged or dev: `%LOCALAPPDATA%\NexRemote`.
  - `--data-dir` overrides both.
  - Resolution happens in `config.py`. Electron passes `--data-dir` explicitly when packaged.
- **Database:** `nexremote.db` (SQLite, SQLModel). Tables:
  - `setting`: key/value JSON.
  - `trusteddevice`: `device_id`, name, public key, first and last connected.
  - `connectionevent`: local audit trail, never sent anywhere.
- **Schema changes:** bump `SCHEMA_VERSION` in `db/engine.py` and add a migration step there. Migrations must be idempotent.
- **Legacy import** (`db/legacy_import.py`) runs once when the DB is empty. It reads the WinUI files:
  - `settings.json` (PascalCase keys)
  - `trusted_devices.json` (timestamps as Unix seconds or ISO strings)
  - the existing `certs/`

  Afterwards it renames them to `*.imported` rather than deleting them. Never regenerate `DeviceId` or the certificate if they already exist: the phones have them pinned.
- Logs go to `logs/nexremote.log`, rotated daily and kept for 30 days.
- **Verified:** the importer has been run against a copy of the real Store 1.0.0.0 LocalState. DeviceId, PC name, legal/consent state, the certificate fingerprint and the trusted phone's key all carried over.

## Commands

**Server** (`windows_app/server/`):

| Task | Command |
|---|---|
| Install | `uv sync` |
| Run (dev) | `uv run nexremote-server --dev` (no auth token; control API on port 51888) |
| Tests | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Freeze | `uv run pyinstaller nexremote-server.spec --noconfirm` (output: `dist/nexremote-server/`) |
| Smoke (manual) | Run the dev server, then `POST /legal/accept`, `POST /consent {"remote_control":true}` on `http://127.0.0.1:51888` before connecting a phone. |

**Desktop** (`windows_app/desktop/`):

| Task | Command |
|---|---|
| Install | `npm install` |
| Dev | `npm run dev` (Next dev server, Electron and the uv-run sidecar together) |
| Lint, typecheck | `npm run lint`, `npm run typecheck` |
| MSIX | `npm run package:appx` (builds Next, compiles Electron, freezes the sidecar, runs electron-builder; output in `desktop/release/`) |

## Store-safety rules

- **Identity:** never change `identityName` (`NeuralNexusStudios.NexRemote`), `publisher` (`CN=8559855F-6955-4418-A6D8-835C3238CF34`) or `publisherDisplayName` (`Neural Nexus Studios`) in `electron-builder.yml` or the AppxManifest template.
- **Versions:** keep the form `Major.Minor.Build.0` and only ever increase them. The current release is `1.1.0.0`.
- **The AppxManifest template must keep:**
  - Capabilities: `runFullTrust`, `internetClient`, `internetClientServer`, `privateNetworkClientServer`, `webcam`.
  - Firewall rules for TCP 8765/8766 and UDP 37020.
  - The `NexRemoteStartup` startup task.
- **Signing and packaging:** don't commit `.pfx` files or signing passwords. Store uploads are re-signed by Microsoft. Sideload tests use a local dev cert whose subject matches the publisher.
- **Product:** no telemetry, ads or accounts. The control API binds to `127.0.0.1` only and requires the token in packaged builds.
- **Python dependencies:** they must freeze with PyInstaller. Check `uv run pyinstaller ...` still works after adding one.

## Feature parity checklist

Every item must work before the legacy `NexRemote/` folder is deleted. Record results in `windows_app/.claude/test-runs.md` (gitignored), and state any gaps plainly.

- **Server lifecycle:** start/stop from the UI and the tray, minimize to tray, single instance, start with Windows.
- **Connection:**
  - UDP discovery reply and QR payload (fields as in the root contract).
  - Pairing a new phone, and reconnecting a trusted one without approval.
  - Approval allow, deny and the 12 s timeout.
  - `MaxClients` rejection, and rejection while remote access is off.
  - Secure port with challenge (DER and raw signatures) and insecure port without one.
- **Input:** keyboard (type, press, release, hotkey), mouse (move, move_relative, click, press, release, scroll), macros.
- **Gamepad:** xinput, dinput and android modes; buttons including `keyboard_*` / `mouse_*` remaps; dpad, sticks, triggers, gyro; `gamepad_mode` reply; ViGEm detection.
- **Screen share:** list_displays, start with display_index(es), fps, quality, resolution, audio; set_* actions; input with normalized and pixel coordinates; `SCRN` frames; `AUDF` audio with `audio_format`.
- **Camera:** consent gate (`permission_required`), list, start, start_multi, stop, stop_all, set_camera, error codes, `CAMF` frames.
- **File explorer:** every action listed in the root contract, with paths kept under drive roots.
- **Task manager:** snapshot (1 s cache), list_processes, system_info, end_process (tree kill; `elevation_required` on access denied).
- **Media control:** every action, plus the `media_info` push every 1.5 s.
- **Clipboard:** get, set, clear.
- **USB:** the adb reverse poller (`<data>\tools\platform-tools\`, then next to the app, then `where adb`).
- **Status:** capabilities and feature_status reflect real availability, including the `action_required` codes.
- **Phone screen (new):** `PSCR` decode in the UI, input relay back to the phone, Back/Home/Recents.
- **Upgrade:** after installing over Store 1.0.0.0, settings, the certificate and trusted devices carry over and the phone reconnects without pairing again.

## Known platform quirks

- **Camera:** OpenCV's MSMF backend fails to open some integrated webcams, so the worker tries DirectShow first and falls back to MSMF. Names and IDs come from WinRT `DeviceInformation`; OpenCV indexes follow the same order.
- **Audio:** WASAPI loopback only delivers `AUDF` chunks while something is actually playing. Silence means no frames, which is the same as the legacy host.
- **Network:** the protocol listeners use uvicorn's `websockets-sansio` implementation with per-message deflate off. JPEG and H.264 don't compress, so deflate would only cost CPU.

## Coding style

- **Python:**
  - Python 3.13 (pinned in `.python-version`; uv downloads it), type hints everywhere, `ruff check` and `ruff format` clean.
  - Asyncio first: blocking Win32/COM/capture calls run in `asyncio.to_thread` or a dedicated thread, never on the event loop.
  - Feature modules expose `async handle(session, msg) -> None` and register with the router by `type`.
  - Wire dicts use the exact snake_case keys. Pydantic models use `populate_by_name`.
- **TypeScript:**
  - Strict mode.
  - Renderer code never imports Node or Electron. All IPC goes through the preload bridge or the control API.
  - UI is Tailwind + shadcn/ui components, restrained, with light and dark themes.
- **Protocol:** changes are additive only and land with the matching client change (see root `AGENTS.md`).

## Memory

Private, gitignored notes go in `windows_app/.claude/`, `.gemini/`, `.codex/`, `.cursor/` and similar folders. Never commit them.
