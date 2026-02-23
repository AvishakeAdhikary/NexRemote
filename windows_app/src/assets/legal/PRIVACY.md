# NexRemote — Privacy Policy

**Last Updated:** February 2026

## 1. Information We Collect

NexRemote operates primarily as a **local-network** tool.  By default, no data
leaves your devices.

| Data Type | Collected? | Details |
|---|---|---|
| Personal identifiers | No | No accounts, no sign-ups. |
| Device name / ID | Locally only | Stored in the config file on YOUR PC for connection pairing. |
| Screen / camera frames | Locally only | Transmitted over your network between your own devices. |
| Keyboard & mouse input | Locally only | Relayed in real time; never stored or logged. |
| File system access | Locally only | File operations happen on your PC; paths are not transmitted externally. |
| Crash logs | Locally only | Stored in `%LOCALAPPDATA%/NexRemote/logs`. Not uploaded. |

## 2. Network Communication

- **Local discovery:** UDP broadcast on port 37020 within your LAN only.
- **WebSocket connections:** Direct WS/WSS connections between your phone and PC.
- **NAT traversal (optional):** If enabled, STUN/TURN servers are contacted to
  establish a connection.  Only connection metadata (IP addresses) is shared
  with those public STUN/TURN servers — no application data.

## 3. Third-Party Services

NexRemote does **not** include analytics, telemetry, or advertising SDKs.

If you enable NAT traversal, Google's public STUN servers
(`stun.l.google.com`) may process your IP address according to Google's
privacy policy.

## 4. Data Storage

All configuration, certificates, and logs are stored locally in:

- **Windows:** `%LOCALAPPDATA%\NexRemote\`

No data is uploaded to any cloud service.

## 5. Your Rights

Since all data stays on your devices, you have full control.  You can delete
the data directory at any time to remove all stored information.

## 6. Children's Privacy

NexRemote is not directed at children under 13.  We do not knowingly collect
information from children.

## 7. Changes to This Policy

We may update this Privacy Policy.  The "Last Updated" date at the top will
reflect any changes.

## 8. Contact

For privacy inquiries: **privacy@neuralnexusstudios.com**
