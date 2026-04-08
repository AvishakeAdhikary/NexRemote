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
