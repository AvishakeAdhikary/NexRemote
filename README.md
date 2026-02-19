<p align="center">
  <img src="windows_app/src/assets/images/logo.png" alt="NexRemote Logo" width="128">
</p>

<h1 align="center">NexRemote</h1>

<p align="center">
  <b>Control your PC from your phone — seamlessly.</b><br>
  Screen sharing · Gamepad · Keyboard & Mouse · Camera · File Transfer
</p>

<p align="center">
  <a href="https://github.com/AvishakeAdhikary/NexRemote/actions"><img src="https://github.com/AvishakeAdhikary/NexRemote/actions/workflows/ci.yml/badge.svg" alt="Build"></a>
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Android-blue" alt="Platform">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🖥 **Screen Sharing** | Live screen streaming with adjustable resolution (up to 4K), FPS (up to 60), and quality |
| 🎮 **Gamepad** | Use your phone as a wireless game controller |
| ⌨️ **Keyboard** | Full keyboard input with special keys and shortcuts |
| 🖱 **Mouse** | Touchpad-style mouse control with gestures |
| 📷 **Camera** | View your PC webcam feed remotely |
| 📂 **File Transfer** | Send and receive files between devices |
| 🔗 **QR Connect** | Instant connection via QR code — no IP typing needed |
| 🔒 **Encrypted** | TLS 1.3 secure connections with fallback support |
| 🌐 **LAN Discovery** | Automatic PC discovery on local network |
| 🆓 **Free & Ad-Free** | No ads, no subscriptions, no telemetry |

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────┐
│                  Windows PC                      │
│  ┌─────────────┐  ┌───────────────────────────┐  │
│  │   PyQt6 GUI │  │   NexRemote Server        │  │
│  │  (Main Loop)│──│  (WebSocket, Async)       │  │
│  │  Start/Stop │  │  Screen Capture · Camera  │  │
│  │  QR Code    │  │  Input Relay · Files      │  │
│  │  Settings   │  │  Discovery (UDP Broadcast)│  │
│  └─────────────┘  └───────────────────────────┘  │
│        │ GUI Thread        │ Server Thread       │
└────────┼───────────────────┼─────────────────────┘
         │                   │
         │   WebSocket (wss / ws fallback)
         │                   │
┌────────┼───────────────────┼─────────────────────┐
│        ▼                   ▼       Android       │
│  ┌───────────────────────────────────────────┐   │
│  │           NexRemote Mobile App            │   │
│  │  QR Scan · LAN Discovery · Gamepad        │   │
│  │  Keyboard · Mouse · Screen View · Camera  │   │
│  └───────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.12+ | Windows PC app |
| **uv** | latest | Python dependency management |
| **Flutter** | 3.x+ | Android mobile app |
| **Android SDK** | API 21+ | Android build |

### 1. Clone the Repository

```bash
git clone https://github.com/AvishakeAdhikary/NexRemote.git
cd NexRemote
```

### 2. Setup Windows App

```powershell
cd windows_app/src
uv sync                    # Creates venv and installs all dependencies
.venv\Scripts\activate     # Activate the environment
uv run main.py             # Launch the application
```

### 3. Setup Mobile App

```bash
cd nexremote
flutter pub get            # Install dependencies
flutter run                # Run on connected device / emulator
```

### 4. Quick Start (Both Apps)

```powershell
.\scripts\dev.ps1          # Starts both apps simultaneously
```

---

## 📱 Connecting

### Method 1: QR Code (Recommended)

1. Click **Start Server** in the Windows app
2. A QR code appears in the app window
3. In the mobile app, tap the **QR scanner icon** on the connection screen
4. Point your camera at the QR code
5. Connected! ✅

### Method 2: LAN Discovery

1. Ensure both devices are on the **same Wi-Fi network**
2. Click **Start Server** on the Windows app
3. Open the mobile app — it will automatically discover available PCs
4. Tap on your PC to connect

---

## 🔨 Building for Production

### Windows Executable

```powershell
.\scripts\build.ps1 -SkipAndroid
# Output: dist/windows/NexRemote.exe
```

### Android APK

```powershell
.\scripts\build.ps1 -SkipWindows
# Output: dist/android/NexRemote.apk
```

### Both Platforms

```powershell
.\scripts\build.ps1
```

---

## 📁 Project Structure

```
NexRemote/
├── windows_app/               # Windows PC application (Python + PyQt6)
│   ├── src/
│   │   ├── main.py            # Application entry point
│   │   ├── core/              # Server, discovery, certs
│   │   ├── ui/                # GUI windows and dialogs
│   │   ├── security/          # Auth, firewall, audit
│   │   ├── utils/             # Config, logging, paths
│   │   └── assets/            # Icons and images
│   └── nexremote.spec         # PyInstaller build config
│
├── nexremote/                 # Android mobile app (Flutter)
│   ├── lib/
│   │   ├── main.dart          # App entry point
│   │   ├── core/              # Connection, discovery
│   │   ├── ui/                # Screens (home, connect, camera, etc.)
│   │   ├── input/             # Controllers (screen share, camera, etc.)
│   │   └── utils/             # Config, logging
│   └── android/               # Android native config
│
├── scripts/                   # Dev and build scripts
│   ├── dev.ps1                # Start both apps for development
│   └── build.ps1              # Production build (EXE + APK)
│
└── .github/workflows/ci.yml  # CI/CD pipeline
```

---

## ⚙️ Configuration

Configuration is stored in:
- **Development:** `windows_app/src/data/config.json`
- **Production (installed):** `%LOCALAPPDATA%\NexRemote\config.json`

| Key | Default | Description |
|-----|---------|-------------|
| `server_port` | `8765` | Secure WebSocket port |
| `server_port_insecure` | `8766` | Fallback WebSocket port |
| `discovery_port` | `37020` | UDP discovery port |
| `max_clients` | `5` | Maximum simultaneous connections |
| `require_approval` | `true` | Require approval for new devices |
| `minimize_to_tray` | `true` | Minimize to system tray on close |

---

## 🔒 Security

- **TLS 1.3** encryption for all WebSocket connections (with insecure fallback for local dev)
- **Self-signed certificates** generated per installation
- **Device trust system** — approve new devices before granting access
- **Audit logging** — all connection events are logged
- **Windows Firewall** rules auto-configured on first launch

---

## 📋 About

**NexRemote** is developed by [**Neural Nexus Studios**](https://github.com/AvishakeAdhikary).

This application is **completely free** and contains **no advertisements** of any kind. If you find NexRemote useful, please consider supporting its development:

<p align="center">
  <a href="https://buymeacoffee.com/avishake69">
    <img src="https://img.shields.io/badge/☕_Buy_Me_a_Coffee-Support_Development-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black" alt="Buy Me a Coffee">
  </a>
</p>

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
