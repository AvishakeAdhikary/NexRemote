# AGENTS.md

Scope: this file applies to the Android client workspace under `client/`, especially the Gradle project in `client/NexRemote/`.

## Mission

NexRemote's Android app is the mobile client for the Windows PC host in `windows_app/`. The Windows app is already published on the Microsoft Store, so treat it as the stable server contract. Your job in this folder is to improve Play production readiness for the Android client without removing features or breaking compatibility with the shipped Windows app.

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

The Windows app in `windows_app/NexRemote/` acts as the server. Read it when needed, but do not modify it unless the user explicitly asks. Preserve these client/server contracts:

- UDP discovery sends `NEXREMOTE_DISCOVER` to port `37020`.
- Discovery responses use JSON fields including `type`, `name`, `port`, `port_insecure`, `id`, `version`, and `cert_fingerprint`.
- WebSocket ports are `8765` for secure `wss` and `8766` for insecure/local fallback `ws`.
- Auth starts with plaintext `auth`, then secure sessions require `auth_challenge` and signed `auth_response`; successful sessions receive `auth_success`.
- Keep support for `auth_failed`, `connection_rejected`, `ping`, and `pong`.
- Client messages after auth are generally encrypted with `CryptoUtils.encryptToBase64`; do not silently change encryption or signing behavior.
- Binary frame headers are `SCRN` for screen frames, `CAMF` for camera frames, and `AUDF` for screen audio frames. Each has a one-byte stream index after the four-byte header.
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

If a feature is intentionally hidden, disabled, or deferred, get explicit user approval and document the reason.

## Optimization Rules

Release builds already enable `isMinifyEnabled = true` and `isShrinkResources = true`. Improve shrinking carefully:

- Prefer removing unused dependencies, unused imports, unused resources, and dead code only after `rg` confirms no references and tests still pass.
- Add R8/ProGuard keep rules only for proven shrinker breakage; keep them narrow.
- Be careful with Kotlin serialization, JSON extension data, dynamic `Map<String, Any?>` payloads, and string-based protocol dispatch. R8 cannot infer server-used message names.
- Do not remove `kotlinx.serialization`, OkHttp, DataStore, AndroidX Security Crypto, Google code scanner, Compose Navigation, or Material/Compose dependencies unless there is a tested replacement.
- Do not add broad permissions or SDKs to solve review issues. Extra sensitive permissions can make Play review harder.
- Keep `android.hardware.camera` optional unless the product requirements change.
- Keep the app free of ads, subscriptions, analytics, and telemetry unless the user explicitly changes the product direction and updates privacy disclosures.
- For tree shaking, measure APK/AAB contents before and after. Prefer App Bundle optimization over feature removal.

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

If you cannot run a command or cannot test with the Windows server, state that clearly in your final response and record the gap in `.gemini/test-runs.md`.

## Coding Style

- Follow existing Kotlin/Compose style and package boundaries.
- Keep changes scoped to Android client files unless explicitly asked otherwise.
- Prefer small, reviewable commits/patches with a clear before/after measurement for optimization work.
- Keep UI changes practical and task-focused; this is a remote-control utility, not a marketing page.
- Preserve legal text and privacy behavior unless the change is deliberate and documented.
