# NexRemote Store Submission Legal Readiness

Last Updated: April 8, 2026

This file summarizes the current legal and policy posture of NexRemote for Microsoft Store and Google Play preparation. It is not a substitute for jurisdiction-specific legal advice, but it is intended to align the app, legal text, and store metadata with the current codebase and the official store-policy materials reviewed during this pass.

## 1. Official References Reviewed

- Microsoft Store Policies: https://learn.microsoft.com/en-us/windows/apps/publish/store-policies
- Support info for MSIX apps: https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/support-info
- Google Play User Data policy: https://support.google.com/googleplay/android-developer/answer/10144311?hl=en
- Google Play Data safety form guidance: https://support.google.com/googleplay/android-developer/answer/10787469?hl=en

## 2. Current Publisher Details

- Legal name: Neural Nexus Studios
- Public publisher name: Neural Nexus Studios
- Principal place of business: Kolkata, West Bengal, India
- Support and privacy email: neural.nex.studios@gmail.com
- Website: https://avishakeadhikary.github.io/Neural-Nexus-Studios/

## 3. Microsoft Store Submission Text

### Website

Use:

`https://avishakeadhikary.github.io/Neural-Nexus-Studios/`

### Support Contact Info

Use:

`neural.nex.studios@gmail.com`

### Privacy Policy

Publish the final privacy policy to a public website URL you control before submission. If you host the repository through GitHub Pages, host the final privacy policy as a public page and use that full URL in Partner Center.

### Certification Notes Recommendation

Use a note similar to:

`NexRemote is a Windows host for user-approved remote control between devices owned or authorized by the user. The app uses local network discovery/listening, remote input, file management, screen sharing, camera streaming, clipboard, task-manager, and optional controller features. Certain controller features may depend on ViGEmBus, which is a separate external dependency. The app does not require an account and does not use a Neural Nexus Studios cloud service for core functionality.`

### Metadata Reminder

At the beginning of the Microsoft Store description, clearly disclose any feature dependency on external components such as ViGEmBus if you continue to offer that feature. This lowers risk under Microsoft’s dependency and accurate-representation rules.

## 4. Google Play Listing Text

### Developer Contact

- Support email: neural.nex.studios@gmail.com
- Website: https://avishakeadhikary.github.io/Neural-Nexus-Studios/

### Privacy Policy URL

Publish the final privacy policy to a public HTML or equivalent web page before Google Play submission. Do not use a private link, PDF-only link, or an unpublished repository path.

## 5. Google Play Data Safety Working Answers

These answers are the recommended starting point for the current codebase. You must confirm the exact Play Console wording at submission time.

### Core position

- NexRemote does not use a developer-hosted account system.
- NexRemote does not send user data to Neural Nexus Studios for analytics, advertising, crash reporting, or backend processing.
- NexRemote transfers data only between devices the user deliberately connects, as part of the core remote-control feature set.

### Recommended declarations

- Data collected by developer or third parties: `No`, based on the current codebase and architecture
- Data shared with other companies or organizations: `No`
- Security practices:
  - do not claim that all app data is always encrypted in transit unless you remove all insecure-connection modes
  - do not claim account-based deletion support, because the app does not currently maintain developer-hosted user accounts
- Data deletion:
  - local deletion is available by clearing app storage or uninstalling the app

### Important caveat

If you later add analytics, crash reporting, cloud sync, relay services, push infrastructure, or any third-party backend processing, you must immediately update both the Data safety form and the privacy policy.

## 6. Recommended Age / Audience Position

For lower policy risk, do not market NexRemote as a child-directed product. The current legal text assumes NexRemote is not directed to children under 13 because the app can expose remote system controls, file management, clipboard data, screen content, camera content, and process information.

## 7. Recommended In-App Disclosure Text

### Android QR camera disclosure

`NexRemote uses the camera only when you choose QR pairing so the app can scan a connection code displayed by your NexRemote PC server. Camera images are processed on your device for scanning and are not sent to Neural Nexus Studios.`

### Windows local network disclosure

`When enabled, NexRemote can listen for connection requests from devices on your local network so you can remotely control a PC you own or are authorized to manage. Disable this feature if you do not want the PC to accept connection attempts.`

### Windows camera streaming disclosure

`NexRemote accesses connected webcams only when you start camera streaming. Camera content is streamed only to the device you choose to connect and is not sent to Neural Nexus Studios.`

### Optional insecure-connection warning

`Secure connection is recommended. If you connect using an insecure mode or insecure port, data on that connection may be less protected on the network.`

## 8. Residual Risks That Documents Alone Do Not Solve

- The public privacy-policy URL must exist and remain reachable before store submission.
- Store listing text, app descriptions, screenshots, and capability declarations must stay consistent with the legal documents.
- Any future backend, analytics, relay, crash-reporting, or advertising change requires immediate policy and metadata updates.
- If external dependencies such as ViGEmBus remain required for certain features, that dependency should be disclosed clearly in store metadata.
- This pass improves compliance posture but is not a substitute for advice from a licensed lawyer in the jurisdictions where you distribute the apps.

## Release 1.1 (November 2026) status

- **Public privacy policy:** https://avishakeadhikary.github.io/Neural-Nexus-Studios/nexremote/privacy/
- **Public terms of service:** https://avishakeadhikary.github.io/Neural-Nexus-Studios/nexremote/terms/

  Both are rendered from `docs/legal/*.md` in the `AvishakeAdhikary/Neural-Nexus-Studios` site repo, under `data/legal/`. Copy updated files there when the policies change.
- **Play declarations for the new Android features:**
  - **Foreground service, `mediaProjection`:** "Share my screen" sends the phone screen to the user's own PC. The service runs only after the user taps Start and accepts Android's capture dialog, and shows an ongoing notification with a Stop action.
  - **Accessibility API:** "NexRemote PC control" performs taps, swipes and Back/Home/Recents sent from the user's paired PC, only while sharing, and only after the in-app prominent disclosure. It reads no content and collects no data. `isAccessibilityTool=false`.
  - **Demo videos:** recorded on a Galaxy A6+ (Android 10) and kept outside git in `dist/store-assets/`:
    - `nexremote-screen-share-fgs-demo.mp4`
    - `nexremote-pc-control-accessibility-demo.mp4`

    Upload them to YouTube (unlisted is fine) and paste the links into the declarations.
- **Data safety, phone screen video and PC-control commands:** processed on the device and sent only to the user's own PC. They are not collected by the developer, so "no data collected" stays accurate. Do not claim "encrypted in transit" while the v1 fallback (`ws://`, legacy fixed-key AES) still exists for older hosts.
- **Android signing:** put `client/NexRemote/keystore.properties` (git-ignored; see `keystore.properties.example`) next to the keystore path, then run `gradlew :app:bundleRelease` to get a signed `app-release.aab` (versionCode 3, 1.1.0).
- **Windows:** `windows_app/desktop/release/NexRemote_1.1.0_x64.appx`, unsigned, for Partner Center upload.
- **Windows firewall:** the manifest opens 8765/8766/37020 for **Private** networks only, the same as 1.0.0.0. On networks marked Public, Windows prompts the user once to allow `nexremote-server.exe`.


### Submission log (2026-11-06)

**Microsoft Store**
- Submission 2 of `9P4RN2KGGJXC` is in certification.
- Package: `NexRemote_1.1.0.0_x64.msixbundle`, a bundle wrapping the 1.1.0.0 appx. The app shipped a bundle before, so updates must be bundles. Target is Windows.Desktop; the 1.0.0.0 bundle stays as the rank-2 fallback.
- `runFullTrust` justification updated for the Electron + `nexremote-server.exe` architecture.
- Listing: description and What's new mention phone screen share (requires Android 1.1). There are four new desktop screenshots with names anonymized, plus box art.
- Properties:
  - Privacy URL switched to the Neural Nexus Studios site.
  - Removed the false "Mixed Reality immersive" display mode.
  - Removed the bogus minimum hardware (touch, NFC, BLE, telephony, mic, Xbox controller, MR). Minimum is now keyboard and mouse; camera stays as recommended.
  - DirectX and VRAM minimums cleared.

**Google Play**
- **Upload key reset:** requested ("forgot keystore password"). The new key (SHA1 `2F:AA:CD:…:2A:45`) becomes valid on 2026-11-07 at 21:48 UTC, and no bundles can be uploaded before then. After that, upload `dist/store-assets/nexremote-1.1.0-vc3.aab` to *Closed testing – Alpha*. A draft release (#4) already exists.
- **After upload:** complete the Foreground service (mediaProjection) and Accessibility declarations that appear for the new bundle, using the video https://youtu.be/H63TporcmqY. Then re-check Data safety and send for review.
- **Privacy policy:** URL switched and sent for review.
- **Production access:** all three closed-test criteria show as met. The application form is pre-filled from an earlier draft with claims about testers (recruitment, engagement, Google Forms feedback). It was deliberately **not** submitted: the developer must confirm those answers are true first.

### Release 1.2 (2026-11-06)

**Microsoft Store**
- Submission 3 is in certification. Submission 2 (1.1.0.0) passed and is live.
- Package: `NexRemote_1.2.0.0_x64.msixbundle`.
- What's new and the description cover:
  - The multi-phone grid.
  - Full-screen phone control.
  - Per-phone audio (needs Android 1.2).
  - Colour palettes.
  - Faster, more accurate Task Manager.
- Four new screenshots in the Nexus red palette, with names anonymized.

**Google Play**
- **Bundle:** upload `dist/store-assets/nexremote-1.2.0-vc4.aab` (1.2.0, versionCode 4, new upload key) instead of the never-uploaded vc3 bundle. The reset key is valid from 2026-11-07 21:48 UTC.
- **New permission:** `RECORD_AUDIO`, used only for AudioPlaybackCapture behind "Let the PC hear this phone". The microphone is never recorded, and the privacy policy (2026-11-06) covers it.
- **Data safety:** keep the "no data collected" position. Phone audio, like the screen, goes only to the user's own PC and never to the developer.
- **Video:** if Play asks about the permission, explain playback capture during screen sharing. The existing FGS (mediaProjection) video still applies.

### Release 1.3 (2026-11-10)

**GitHub Releases**
- `v1.3.0` is the first installable CI APK. It is signed with a dedicated sideload key (repo secrets; local copy `C:\Projects\Execution\github-sideload.jks`), never the Play upload key. Downloaded from the public `releases/latest` link, installed on a Galaxy A6+, and tested against the 1.3 host: discovery, pairing, encrypted session, task manager, touchpad.

**Microsoft Store**
- Submission 4 (`NexRemote_1.3.0.0_x64.msixbundle`) is in certification. 1.2.0.0 is live.

**Google Play (sent for review 2026-11-10)**
- Release 4 on *Closed testing – Alpha* holds `nexremote-1.3.0-vc6.aab` (1.3.0, versionCode 6). Its internal release name still reads "5 (1.3.0)". vc5 was uploaded and removed from the draft, and it dropped 12 devices because `RECORD_AUDIO` implied a required microphone. vc6 marks the microphone optional and drops none.
- **Demo video:** https://youtu.be/Sfdjx1l4bKU (unlisted, Neural Nexus Studios channel; source `dist/store-assets/nexremote-1.3-demo.mp4`). It shows the 1.3 Windows and Android apps side by side:
  - pairing approval
  - MediaProjection consent and the ongoing Stop notification
  - the in-app PC-control disclosure
  - enabling the service in Accessibility settings
  - PC Home / Recents / tap / Back
  - Stop from the notification

  Notification-shade contents other than NexRemote's are blurred, and the devices are shown as "My phone" and "My PC".
- **Declarations:** both use that video.
  - Foreground service: media projection.
  - Accessibility: App functionality; no personal or sensitive data collected or shared; disclosure-video acknowledgement ticked.
- The old tour video (H63TporcmqY) was deleted at the owner's request.

### Android 1.3.1 (2026-11-10)
- **Fixes:**
  - The 1.3.0 release build crashed when the QR scanner opened. R8 broke the ML Kit code-scanner client; keep rules were added.
  - The scanner module is now requested at install, with a bundled ZXing fallback.
  - The device-name field can now be cleared.
- **GitHub:** tag `v1.3.1`.
- **Play:** release 5 on *Closed testing – Alpha* (`nexremote-1.3.1-vc7.aab`, versionCode 7) was sent for review the same day. It drops no devices, and the declarations are unchanged.
