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

## UI Toolkit

The UI uses **Composables UI** (`com.composables:ui`, built on Compose Unstyled), not Material 3. `androidx.compose.material3` is not a dependency; don't add it back.

- Theme: `ui/theme/Theme.kt` builds `NexRemoteTheme` with composeunstyled `buildTheme`, filling the Composables UI tokens (`com.composables.ui.theme.*`) with a red-on-black palette plus NexRemote tokens (`accentSoftColor`, `successColor`, `warningColor`, `panelRaisedColor`). Dark is the default; `ThemeMode` (Dark/Light/System) is a setting in `AppPreferences`. Inside `buildTheme`, refer to `com.composables.ui.theme.defaultIndication` and `defaultTextSelectionColors` by their full names, because the builder has same-named properties.
- Design kit: `ui/design/Nx.kt` holds `Nx` (colours), `NxType` (type scale), `NxScaffold`/`NxTopBar`, `NxCard`, `NxButton`, `NxChip`, `NxSegmented`, `NxTextField` (a String adapter over the state-based TextField), `NxDialog`, `NxSpinner`, and `NxSnackbarState`. Home, Connection, Settings, Legal and the gamepad editor use it directly.
- Migration bridge: `ui/design/compat/Bridge.kt` gives the remaining screens Material-shaped names (`Card`, `Button`, `Scaffold`, `MaterialTheme.typography`, ...) rendered with Composables UI. Port screens to `Nx*` over time and delete bridge entries when their last caller goes.
- Composables UI's `Toolbar` doesn't constrain the title against its trailing actions, so use `NxTopBar`.
- Gamepad: play and editor share `padBounds()`, `GamepadCanvasBox` and `GamepadLandscapeFrame` (in `GamepadScreen.kt`), so the editor canvas always matches the play canvas. Round controls (joystick, D-pad, face buttons) are kept square, and their inner buttons are sized as a fraction of the cluster. Landscape is immersive. The editor renders in place of the play screen, not in a Dialog.
- **Haptics** (`ui/components/Haptics.kt`) follow https://developer.android.com/develop/ui/views/haptics/haptic-feedback:
  - Ordinary UI uses `View.performHapticFeedback` with press/release constants, which honours the system Touch-feedback setting.
  - The gamepad (`rememberAppHaptics(..., game = true)`) plays predefined `VibrationEffect`s with game/media attributes, so the per-layout "Vibrate on press" switch works even when system touch feedback is off.
  - Don't use `CLOCK_TICK` for presses; it's too faint on many motors.
- **Dialogs:** Composables UI's `AlertDialog` measures its body with unbounded height. Never put a `LazyColumn` (or another `verticalScroll`) inside it, because it crashes. Use a bottom panel with a bounded height (see `LayoutPickerPanel`).
- **Touchpad:**
  - Custom gestures with no touch slop: one-finger move with acceleration (`pointerGain`), tap/long-press clicks, two-finger tap = right click, two-finger drag = scroll.
  - Scroll uses `precise: true` only when the host advertises `precise_scroll`.
  - Sockets use `NoDelaySocketFactory` (TCP_NODELAY). Without it, Nagle plus Windows delayed ACKs add up to 200 ms per touchpad move.
- **Charts:** Vico (`com.patrykandpatrick.vico:compose`). The task-manager history lives in `TaskManagerRepository.history`, with a fixed 60-sample window so lines enter from the right.
- **QR pairing** (`ConnectionScreen.kt`):
  - Google's code scanner (`play-services-code-scanner`) is tried first. It is an optional Play services module, which the manifest asks for at install time (`com.google.mlkit.vision.DEPENDENCIES = barcode_ui`). The app checks it with `ModuleInstall` and, when it's missing or fails (for example "Waiting for the Barcode UI module to be downloaded", or no Play services), falls back to the bundled ZXing scanner (`com.journeyapps:zxing-android-embedded`, `ScanContract`).
  - Never swallow scanner failures silently.
  - `proguard-rules.pro` keeps the ML Kit code-scanner packages. Without them, the R8 release build crashed with an NPE as soon as the scanner client was created.
  - ZXing adds optional camera/screen features; keep them all `required="false"` (check the merged manifest).
- **Text fields:** `NxTextField` compares edits against the current value (`rememberUpdatedState`). Screens keep their own editing state rather than keying `remember` to a saved value: the device-name field used to snap back to the system name whenever it was cleared.
- **Phone audio** (`service/PhoneAudioCapture.kt`): AudioPlaybackCapture on the share's MediaProjection, Android 10+, `RECORD_AUDIO` granted from the "Let the PC hear this phone" switch. Never the microphone.
- Toolchain: Composables UI requires Kotlin 2.4 (the root `build.gradle.kts` pins the Kotlin Gradle plugin through the catalog) and `compileSdk` 37 (`targetSdk` stays 36).

Use the existing Gradle wrapper from `client/NexRemote/`.

## Server Contract

The Windows host is `windows_app/server/` (Python/FastAPI, the protocol server) with `windows_app/desktop/` (Electron UI). The WinUI host that shipped as Store 1.0.0.0 has been removed from the repo (git history keeps it); the root `AGENTS.md` wire contract describes its v1 behaviour. Protocol changes must land in the client and `windows_app/server/` together (see root `AGENTS.md`). Preserve these client/server contracts:

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
- Do not remove `kotlinx.serialization`, OkHttp, Google code scanner, Compose Navigation, Composables UI or the View-based Material library (used by the XML window theme) unless there is a tested replacement. (Storage is plain `SharedPreferences`; DataStore and Security Crypto are not dependencies.)
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
- Release build: `.\gradlew.bat :app:assembleRelease` (signed only when `keystore.properties` exists; see `keystore.properties.example`. That file is git-ignored and must never be committed).
- Lint, when relevant: `.\gradlew.bat :app:lint`

For release-readiness work, also manually verify against the current Windows Store server build when possible:

- Discover PC over Wi-Fi.
- Connect by QR/manual IP and by USB localhost.
- Accept/reject/timeout approval flow.
- Secure connection, insecure fallback, certificate mismatch handling, reconnect, and disconnect.
- Every feature listed above, including binary screen/camera/audio streams.
- Phone screen share: start, rotation, Stop from the notification, PC control on/off, taps, swipes and Back/Home/Recents from the PC.
- Against the Store 1.0.0.0 host: everything except phone screen share still works (legacy crypto fallback).

Environment notes (Windows dev machine):

- Needs JDK 17+ (a portable Temurin 21 works: set `JAVA_HOME`) and the SDK from the `android` CLI (`android sdk install platforms/android-36.1 build-tools/36.1.0`). Point Gradle at the SDK with `ANDROID_HOME`; don't commit `local.properties`.
- If the Gradle wrapper download times out from Java but `curl` works, set `JAVA_TOOL_OPTIONS=-Djava.net.preferIPv4Stack=true`.
- On-device testing: prefer a real phone over an emulator (the owner's choice). Drive it with `adb` and `android layout`/`screencap`.
- `android layout` (UiAutomation) temporarily suppresses other accessibility services. While a layout dump runs, `NexRemoteControlService` unbinds, and the app shows PC control as "not set up". Verify PC control with `adb shell dumpsys activity activities` instead of layout dumps.
- Simulating an older client: build `master` in a temporary `git worktree` and `adb install -r -d` it. The `.debug` id and debug key match, so trusted pairing carries over.

If you cannot run a command or cannot test with the Windows server, state that clearly in your final response and record the gap in `.gemini/test-runs.md`.

## Coding Style

- Follow existing Kotlin/Compose style and package boundaries.
- Keep changes scoped to Android client files unless explicitly asked otherwise.
- Prefer small, reviewable commits/patches with a clear before/after measurement for optimization work.
- Keep UI changes practical and task-focused; this is a remote-control utility, not a marketing page.
- Preserve legal text and privacy behavior unless the change is deliberate and documented.
