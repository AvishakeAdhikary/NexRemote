# AGENTS.md

Scope: this file applies to the Windows host workspace under `windows_app/`, especially the WinUI/.NET project in `windows_app/NexRemote/`.

## Mission

The Windows app is the NexRemote PC host/server and is already published on the Microsoft Store. Treat it as the stable production side of the product. For Android client optimization work, this folder is primarily read-only protocol reference. Do not change Windows app code, package identity, signing settings, assets, legal text, publish profiles, or runtime behavior unless the user explicitly asks for Windows changes.

If a future task does require Windows changes, keep them backward-compatible with the Android client and Microsoft Store release expectations.

## Memory

Use private, gitignored agent memory for protocol notes, build notes, and manual test checklists. The repository root intentionally ignores common local-agent folders.

Preferred memory directories:

- Gemini: `windows_app/.gemini/`
- Claude: `windows_app/.claude/`
- Codex: `windows_app/.codex/`
- Cursor: `windows_app/.cursor/`
- Windsurf: `windows_app/.windsurf/`
- Aider: `windows_app/.aider/`
- Continue: `windows_app/.continue/`
- Augment, Qodo, and Kilo Code: `windows_app/.augment/`, `windows_app/.qodo/`, `windows_app/.kilocode/`

Do not commit files from these directories, generated scratch logs, local certificates, signing material, personal tester data, or machine-specific paths.

Suggested memory layout for longer work:

- `windows_app/.gemini/context.md` for stable server/project notes.
- `windows_app/.gemini/protocol-contract.md` for client/server compatibility notes.
- `windows_app/.gemini/test-runs.md` for build and manual integration results.

If the executing agent is Claude, Codex, Cursor, Windsurf, Aider, Continue, Augment, Qodo, or Kilo Code, mirror short-lived notes in that agent's own directory when useful. Keep this Windows app treated as protocol reference for Android client work unless the user explicitly asks for Windows changes.

Keep durable project documentation outside `.gemini/` only when the user explicitly asks for it.

## Project Shape

The live Windows app is a WinUI 3/.NET host, not the older Python layout described in the root README.

- Solution: `windows_app/NexRemote/NexRemote.slnx`
- App project: `windows_app/NexRemote/NexRemote/NexRemote.csproj`
- Window/UI: `MainWindow.xaml`, `MainWindow.cs`, `ViewModels/`
- Server host: `Services/RemoteServerHost*.cs`
- Protocol constants: `Services/ProtocolConstants.cs`
- JSON options: `Services/ProtocolJson.cs`
- Discovery and QR payloads: `Services/DiscoveryService.cs`, `Services/DiscoveryModelFactory.cs`, `Models/DiscoveryResponse.cs`, `Models/QrConnectionPayload.cs`
- Capabilities/feature status: `Models/CapabilitiesModel.cs`, `Models/FeatureStatusInfo.cs`, `Services/ServerCapabilitiesFactory.cs`
- Store/package metadata: `Package.appxmanifest`, `Properties/PublishProfiles/`, app assets, and signing properties in the project file.

## Store-Safety Rules

Because this app is already on the Microsoft Store:

- Do not change `Package.appxmanifest`, package identity, signing thumbprints, temporary keys, publish profiles, app logos, Store assets, or legal documents without explicit approval.
- Do not change default ports, protocol message names, JSON property names, binary frame headers, encryption, trust, or approval behavior unless the Android client is updated compatibly and the user approves the release plan.
- Do not remove services just because a feature appears optional. Android client review/optimization work must not shrink the server.
- Do not add telemetry, ads, account systems, or network services unrelated to the local remote-control workflow unless explicitly requested and documented.
- Do not place secrets, certificates, or signing material in `.gemini/` or new committed files.

## Client/Server Contract

Preserve these contracts used by the Android client:

- UDP discovery magic: `NEXREMOTE_DISCOVER`.
- Default discovery port: `37020`.
- Default secure WebSocket port: `8765`.
- Default insecure WebSocket port: `8766`.
- Discovery/QR fields include `type`, `host`, `name`, `port`, `port_insecure`, `id`, `version`, and `cert_fingerprint`.
- Auth message types include `auth`, `auth_challenge`, `auth_response`, `auth_success`, `auth_failed`, and `connection_rejected`.
- Liveness messages are `ping` and `pong`.
- Main command types include `keyboard`, `mouse`, `gamepad`, `gamepad_xinput`, `gamepad_dinput`, `gamepad_android`, `gamepad_mode`, `macro`, `camera`, `file_explorer`, `screen_share`, `media_control`, `task_manager`, and `clipboard`.
- Binary frame headers are `SCRN`, `CAMF`, and `AUDF`, followed by a one-byte index and then payload bytes.
- JSON uses explicit `JsonPropertyName` snake_case fields and `ProtocolJson.SharedOptions`; preserve wire names even when C# property names differ.
- Feature status and capability fields are consumed by the Android home screen to enable, disable, and explain features.

## Server Features

The server hosts or coordinates:

- TLS/insecure WebSocket hosting and local-network discovery.
- Device trust, approval timeout, public-key challenge/response, and connection rejection.
- Native keyboard/mouse input, macro replay, and screen-share input.
- Gamepad transport, xinput/dinput/android modes, and ViGEm availability reporting.
- Screen capture, multiple displays, frame quality/FPS/resolution, and screen audio capture.
- Camera capture and camera permission/consent handling.
- File explorer operations.
- Task manager operations.
- Media controls and clipboard operations.
- QR payload generation, tray behavior, app settings, theme, logging, and legal document display.

Do not break any of these when making server-side changes.

## Build And Verification

Run commands from `windows_app/NexRemote/`.

- Restore/build when needed: `dotnet build .\NexRemote.slnx -c Debug -p:Platform=x64`
- Release/package work should follow the existing `.pubxml` profiles and Store signing setup only when explicitly requested.

Manual compatibility checks matter more than isolated compilation for protocol changes:

- Start/stop server.
- Confirm UDP discovery and QR payload.
- Pair a new Android client and reconnect a trusted one.
- Verify approval allow/deny/timeout.
- Verify secure and insecure connections.
- Exercise every command type listed in the contract.
- Verify screen, camera, and audio binary frames are still parsed by Android.
- Confirm feature status/capabilities match actual availability.

If you cannot test with the Android client, state the gap clearly and record it in `windows_app/.gemini/test-runs.md`.

## Coding Style

- Follow existing C# nullable-enabled style and service boundaries.
- Keep protocol changes additive and backward-compatible.
- Prefer explicit JSON property names for anything crossing the wire.
- Keep UI changes restrained and consistent with the current WinUI app.
- Avoid broad refactors in Store-published paths unless the task requires them.
