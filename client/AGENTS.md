# AGENTS.md

Scope: this file applies to the Android client workspace under `client/`, especially the Gradle project in `client/NexRemote/`.

## Mission

NexRemote's Android app is the mobile client for the Windows PC host in `windows_app/`. The Windows app is published on the Microsoft Store (v1.0.0.0 WinUI host; v1.1.0.0 is the Electron + Python rebuild). Both host versions must keep working with this client. Your job in this folder is to ship features and improve Play production readiness without removing features or breaking compatibility with either host.

The full wire contract lives in the root `AGENTS.md`. This file covers Android-specific rules.

Focus on measurable client quality work: app size reduction, R8/resource shrinking, startup/runtime performance, reliability, policy clarity, permission clarity, and review evidence. Do not attempt to bypass Google Play review, fake tester engagement, fake installs, or invent closed-test feedback. When production-application answers are needed, draft truthful responses only from facts supplied by the owner or evidence you can gather from the repo/testing.

## Memory

Use private, gitignored agent memory for analysis notes, APK size notes, Play Console answer drafts, and task checklists. The repository root intentionally ignores common local-agent folders.

Preferred memory directories:

- Gemini: `client/.gemini/`
- Claude: `client/.claude/`
- Codex: `client/.codex/`
- Cursor: `client/.cursor/`
- Windsurf: `client/.windsurf/`
- Aider: `client/.aider/`
- Continue: `client/.continue/`
- Augment, Qodo, and Kilo Code: `client/.augment/`, `client/.qodo/`, `client/.kilocode/`

Do not commit files from these directories, generated scratch logs, personal tester data, credentials, keystores, or local machine paths.

Suggested memory layout for longer work:

- `client/.gemini/context.md` for stable project notes.
- `client/.gemini/CLIENT-PRODUCTION-QA.md` for the exact Play Console production questions, current draft answers, owner-input gaps, and supporting evidence.
- `client/.gemini/play-production-notes.md` for broader truthful notes mapped to the recurring Play Console questions.
- `client/.gemini/size-analysis.md` for before/after APK or AAB size measurements.
- `client/.gemini/test-runs.md` for commands, devices, and manual test outcomes.

Keep `client/.gemini/CLIENT-PRODUCTION-QA.md` updated whenever you learn facts about closed testing, tester recruitment, feedback, changes made, readiness criteria, or production expectations. Never invent tester activity or feedback.

If the executing agent is Claude, Codex, Cursor, Windsurf, Aider, Continue, Augment, Qodo, or Kilo Code, mirror short-lived notes in that agent's own directory when useful, but keep `client/.gemini/CLIENT-PRODUCTION-QA.md` as the source-of-truth Play production QA file for this handoff unless the user says otherwise.

Keep durable project documentation outside `.gemini/` only when the user explicitly asks for it.

## Project Shape

The live Android client is Kotlin/Jetpack Compose, not the older Flutter layout described in the root README.

- Gradle root: `client/NexRemote/`
- Main module: `client/NexRemote/app/`
- App package: `com.neuralnexusstudios.nex_remote`
- UI entry/navigation: `app/src/main/java/com/neuralnexusstudios/nex_remote/ui/NexRemoteApp.kt`
- Dependency container: `app/src/main/java/com/neuralnexusstudios/nex_remote/core/AppContainer.kt`
- Network/discovery: `core/network/`
- Feature repositories: `core/feature/`
- Models and serialized protocol data: `core/model/Models.kt`
- Legal assets: `docs/` and `app/src/main/assets/legal/`

Use the existing Gradle wrapper from `client/NexRemote/`.

## Server Contract

The Windows host is `windows_app/server/` (Python/FastAPI, the protocol server) with `windows_app/desktop/` (Electron UI). The legacy WinUI host in `windows_app/NexRemote/` is still the reference for v1 behaviour until it is deleted. Protocol changes must land in the client and `windows_app/server/` together (see root `AGENTS.md`). Preserve these client/server contracts:

- UDP discovery sends `NEXREMOTE_DISCOVER` to port `37020`.
- Discovery responses use JSON fields including `type`, `name`, `port`, `port_insecure`, `id`, `version`, and `cert_fingerprint`.
- WebSocket ports are `8765` for secure `wss` and `8766` for insecure/local fallback `ws`.
- Auth starts with plaintext `auth`, then secure sessions require `auth_challenge` and signed `auth_response`; successful sessions receive `auth_success`.
- Keep support for `auth_failed`, `connection_rejected`, `ping`, and `pong`.
- Client messages after auth are encrypted. Legacy v1 uses `CryptoUtils.encryptToBase64` (fixed key, zero IV). When the host's `auth_success` contains `server_ephemeral_key` and `session_crypto: "aes-256-gcm"`, the client switches to the negotiated v2 session cipher (`core/network/SessionCrypto.kt`). If those fields are missing (the Store 1.0.0.0 host), it must fall back to legacy. Don't change either scheme without changing the server too.
- Binary frame headers are `SCRN` for screen frames, `CAMF` for camera frames, and `AUDF` for screen audio frames (host → client), and `PSCR` for phone screen video (client → host: flags byte, 8-byte big-endian pts in µs, H.264 Annex-B). Each has a one-byte stream index after the four-byte header.
- Only start phone screen share when the host advertises `capabilities.phone_screen`. Old hosts don't, so hide or disable the feature there with a clear "update NexRemote on your PC" message.
- JSON field names using snake_case are protocol names. Do not rename them for Kotlin style unless `@SerialName` or explicit map keys preserve the wire format.

## Features That Must Not Be Removed

Optimization must preserve the visible feature set:

- Terms/privacy acceptance flow.
- Wi-Fi discovery, QR/manual connection, USB localhost connection, secure certificate trust, and reconnect behavior.
- Mouse/touchpad, keyboard, hotkeys, clicks, scroll, and screen-share pointer input.
- Media playback and volume controls.
- Screen share, multiple displays, quality/FPS/resolution controls, and PC audio streaming.
- Camera list/start/stop/multi-camera flows and camera permission disclosure.
- File explorer drive/list/search/open/read/write/create/rename/delete/copy/move/properties flows.
- Task manager snapshot/process/system-info/end-process flows.
- Gamepad layouts, custom layout storage, xinput/dinput/android modes, dpad/buttons/sticks/triggers/gyro, and macros.
- Feature availability/status messaging from the server.
- Phone screen share to the PC (MediaProjection + foreground service + H.264), and optional PC-side remote control of the phone (AccessibilityService, off by default, behind a prominent disclosure).

If a feature is intentionally hidden, disabled, or deferred, get explicit user approval and document the reason.

## Optimization Rules

Release builds already enable `isMinifyEnabled = true` and `isShrinkResources = true`. Improve shrinking carefully:

- Prefer removing unused dependencies, unused imports, unused resources, and dead code only after `rg` confirms no references and tests still pass.
- Add R8/ProGuard keep rules only for proven shrinker breakage; keep them narrow.
- Be careful with Kotlin serialization, JSON extension data, dynamic `Map<String, Any?>` payloads, and string-based protocol dispatch. R8 cannot infer server-used message names.
- Do not remove `kotlinx.serialization`, OkHttp, Google code scanner, Compose Navigation, or Material/Compose dependencies unless there is a tested replacement. (Storage is plain `SharedPreferences`; DataStore and Security Crypto are not dependencies.)
- Do not add broad permissions or SDKs to solve review issues. Extra sensitive permissions can make Play review harder.
- Keep `android.hardware.camera` optional unless the product requirements change.
- Keep the app free of ads, subscriptions, analytics, and telemetry unless the user explicitly changes the product direction and updates privacy disclosures.
- For tree shaking, measure APK/AAB contents before and after. Prefer App Bundle optimization over feature removal.

## Sensitive Components And Play Policy Duties

The phone screen share and remote-control features use components that Play reviews closely. Keep them exactly this narrow:

- **Screen share:** `service/ScreenCastService.kt` is a foreground service with `foregroundServiceType="mediaProjection"`.
  - Permissions: `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_MEDIA_PROJECTION`, `POST_NOTIFICATIONS`.
  - It starts only after the user taps Start and accepts the system MediaProjection dialog. On Android 14+ it needs a fresh consent token each session.
  - While sharing it shows an ongoing notification with a Stop action. Video goes only to the connected PC.
- **Remote control:** `service/NexRemoteControlService.kt` is an AccessibilityService. Its config has `canPerformGestures="true"` and `isAccessibilityTool="false"`, and it requests no event types beyond what gestures need. It never reads screen content or window text.
  - It is enabled only after the in-app prominent disclosure screen. That screen states what the service does, that it only acts on input from the user's paired PC while sharing, and that no data is collected. The user must then explicitly agree before being sent to system settings.
  - It ignores all input unless a phone-screen session is active and "Allow PC control" is on.
- **Play Console:** both components need declarations: the foreground-service declaration (media projection) and the Accessibility API declaration (remote control of the user's own device). Each needs a short demo video. The privacy policy and Data safety form must describe screen capture: processed on the device and sent only to the user's own PC, never to the developer. Keep `docs/legal/` and `app/src/main/assets/legal/` in sync with this.
- **Network security:** `res/xml/network_security_config.xml` allows cleartext, because the LAN `ws://` fallback and the USB `ws://127.0.0.1:8766` path need it. TLS trust uses certificate pinning inside the TrustManager. Never reintroduce a trust-all `X509TrustManager` or `HostnameVerifier`, which Play flags as unsafe.

## Play Production Readiness

The owner is repeatedly asked these Play Console questions:

1. How testers were recruited.
2. How easy recruitment was.
3. Tester engagement and realistic usage.
4. Feedback summary and collection method.
5. Intended audience.
6. User value.
7. Expected first-year installs.
8. Changes made from closed testing.
9. Why the app is ready for production.
10. What was done differently this time.

When helping with this, collect facts and produce evidence. Do not fabricate. Useful client changes for this situation include:

- Clearer onboarding and connection guidance.
- Clear permission explanations for camera, local network, wake lock, and QR scanning.
- Better error states for server not found, approval timeout, certificate mismatch, Wi-Fi disabled, and unavailable PC features.
- Crash fixes and reconnection fixes.
- Responsive UI fixes across phones/tablets/orientations.
- Release-size and startup improvements.
- A concise changelog of closed-test-driven improvements in `.gemini/play-production-notes.md`.

The exact questions and working answer draft belong in `client/.gemini/CLIENT-PRODUCTION-QA.md`. Before a production application is submitted, make sure each answer is specific, factual, and backed by tester notes, build/test evidence, screenshots, issue lists, or owner-provided facts.

## Build And Verification

Run commands from `client/NexRemote/`.

- Unit tests: `.\gradlew.bat :app:testDebugUnitTest`
- Debug build: `.\gradlew.bat :app:assembleDebug`
- Release build: `.\gradlew.bat :app:assembleRelease`
- Lint, when relevant: `.\gradlew.bat :app:lint`

For release-readiness work, also manually verify against the current Windows Store server build when possible:

- Discover PC over Wi-Fi.
- Connect by QR/manual IP and by USB localhost.
- Accept/reject/timeout approval flow.
- Secure connection, insecure fallback, certificate mismatch handling, reconnect, and disconnect.
- Every feature listed above, including binary screen/camera/audio streams.
- Phone screen share: start, rotation, Stop from the notification, PC control on/off, taps, swipes and Back/Home/Recents from the PC.
- Against the Store 1.0.0.0 host: everything except phone screen share still works (legacy crypto fallback).

If you cannot run a command or cannot test with the Windows server, state that clearly in your final response and record the gap in `.gemini/test-runs.md`.

## Coding Style

- Follow existing Kotlin/Compose style and package boundaries.
- Keep changes scoped to Android client files unless explicitly asked otherwise.
- Prefer small, reviewable commits/patches with a clear before/after measurement for optimization work.
- Keep UI changes practical and task-focused; this is a remote-control utility, not a marketing page.
- Preserve legal text and privacy behavior unless the change is deliberate and documented.
