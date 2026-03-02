# NexRemote — Privacy Policy

**Last Updated:** February 28, 2026  
**Effective Date:** February 28, 2026

---

## 1. Introduction

This Privacy Policy explains how **Neural Nexus Studios** ("we," "us," "our")
handles information when you use NexRemote ("the Application").  We are
committed to protecting your privacy.

NexRemote is designed as a **local-first** application.  By default, **no data
leaves your devices** or is transmitted to our servers.

## 2. Information We Collect

| Data Type | Collected? | Details |
|---|---|---|
| Personal identifiers | **No** | No accounts, no sign-ups, no email collection. |
| Device name / ID | Locally only | Stored in the local config file for connection pairing. |
| Screen / camera frames | Locally only | Transmitted over your network between your own devices. Never stored or logged. |
| Keyboard & mouse input | Locally only | Relayed in real time; never stored, logged, or transmitted externally. |
| File system access | Locally only | File operations happen on your PC; paths are not transmitted externally. |
| Crash logs | Locally only | Stored on your device only. Not uploaded or shared. |
| Usage analytics | **No** | No analytics, telemetry, or tracking of any kind. |
| Advertising identifiers | **No** | No advertising SDKs are included. |

## 3. How We Use Information

Since we collect no data, there is nothing to "use."  All information generated
by NexRemote stays on your devices and under your control.

## 4. Network Communication

- **Local discovery:** UDP broadcast on port 37020 within your LAN only.
- **WebSocket connections:** Direct WS/WSS connections between your phone and
  PC.  These connections use TLS/SSL encryption where supported.
- **Keep-alive pings:** The client sends periodic ping messages to maintain the
  connection.  These contain no user data.
- **NAT traversal (optional):** If enabled, STUN/TURN servers are contacted to
  establish a peer-to-peer connection.  Only connection metadata (IP addresses)
  is shared with those servers — no application data.

## 5. Third-Party Services

NexRemote does **not** include:

- Analytics or telemetry SDKs
- Advertising networks
- User tracking or fingerprinting
- Social media integrations

**STUN/TURN servers:** If you enable NAT traversal, Google's public STUN servers
(`stun.l.google.com`) may process your IP address.  Their usage is governed by
[Google's Privacy Policy](https://policies.google.com/privacy).

## 6. Data Storage

All configuration, certificates, and logs are stored locally:

| Platform | Location |
|---|---|
| **Windows (server)** | `%LOCALAPPDATA%\NexRemote\` |
| **Android (client)** | App-private storage (accessible via Android Settings → Apps → NexRemote → Storage) |

No data is uploaded to any cloud service, remote server, or third-party
platform.

## 7. Data Retention

Data persists only as long as the Application is installed.  Uninstalling
NexRemote removes all locally stored data.  You can also manually delete the
data directories listed above at any time.

## 8. Your Rights

### For all users

Since all data remains on your devices, you have complete control.  You may
delete the data directory at any time to remove all stored information.

### For users in the European Union (GDPR)

Under the General Data Protection Regulation, you have the right to access,
rectify, erase, restrict processing of, and port your personal data.  Because
NexRemote does not collect or process personal data, these rights are inherently
satisfied.  If you have questions, contact us at the address below.

### For California residents (CCPA)

Under the California Consumer Privacy Act, you have the right to know what
personal information is collected, request deletion, and opt out of its sale.
NexRemote does **not** collect, sell, or share personal information as defined
by the CCPA.

## 9. Children's Privacy (COPPA)

NexRemote is not directed at children under 13.  We do not knowingly collect
any information — personal or otherwise — from children under 13.  If you
believe a child under 13 has provided information through the Application,
please contact us so we can take appropriate action.

## 10. International Data Transfer

NexRemote does not transfer data internationally.  All data stays on your local
devices and network.

## 11. Security

We implement reasonable technical measures to protect data in transit between
your devices:

- **TLS/SSL encryption** for WebSocket connections (wss://)
- **AES encryption** for message payloads
- **Self-signed certificates** generated locally during first run

You are responsible for the security of your local network and devices.

## 12. Changes to This Policy

We may update this Privacy Policy.  The "Last Updated" date at the top will
reflect any changes.  Continued use of the Application after changes constitutes
acceptance of the revised policy.

## 13. Contact

For privacy inquiries: **privacy@neuralnexusstudios.com**
