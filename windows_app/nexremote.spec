# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for NexRemote Windows Application.

Build with:
    pyinstaller nexremote.spec --noconfirm

Or via the build script:
    .\scripts\build.ps1
"""
import os
import importlib.util

block_cipher = None

# ── Locate vgamepad native DLLs and data ──────────────────────────────────
# vgamepad ships ViGEmClient.dll which must be bundled, or the import crashes.
vgamepad_binaries = []
_vg_spec = importlib.util.find_spec('vgamepad')
if _vg_spec and _vg_spec.submodule_search_locations:
    _vg_root = _vg_spec.submodule_search_locations[0]
    # ViGEmClient.dll files (x64 + x86)
    for arch in ('x64', 'x86'):
        dll_path = os.path.join(_vg_root, 'win', 'vigem', 'client', arch, 'ViGEmClient.dll')
        if os.path.isfile(dll_path):
            vgamepad_binaries.append((dll_path, os.path.join('vgamepad', 'win', 'vigem', 'client', arch)))

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=vgamepad_binaries,
    datas=[
        # Bundle static assets (images, legal docs, etc.)
        ('src/assets', 'assets'),
        # Bundle the elevated-operations helper module
        ('src/utils/elevated_ops.py', 'utils'),
    ],
    hiddenimports=[
        # ── Application modules ─────────────────────────────────
        # PyInstaller cannot auto-discover these because it only
        # follows direct imports from main.py. Lazy / conditional
        # imports and the implicit package structure cause misses.
        
        # core
        'core.server',
        'core.server_thread',
        'core.discovery',
        'core.connection_manager',
        'core.certificate_manager',
        'core.usb_detector',
        'core.nat_traversal',
        
        # ui
        'ui.main_window',
        'ui.settings_dialog',
        'ui.connection_dialog',
        'ui.terms_dialog',
        'ui.tray_icon',
        'ui.file_explorer',
        'ui.task_manager',
        
        # security
        'security.encryption',
        'security.authentication',
        'security.audit_logger',
        'security.firewall_config',
        
        # input
        'input.virtual_keyboard',
        'input.virtual_mouse',
        'input.virtual_gamepad',
        'input.media_controller',
        'input.input_validator',
        
        # streaming
        'streaming.screen_capture',
        'streaming.camera_streamer',
        'streaming.audio_capture',
        'streaming.virtual_camera',
        
        # utils
        'utils.paths',
        'utils.config',
        'utils.logger',
        'utils.elevate',
        'utils.elevated_ops',
        'utils.protocol',
        'utils.vigem_setup',
        
        # ── Third-party dependencies ────────────────────────────
        # Qt
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        
        # Networking
        'websockets',
        'websockets.legacy',
        'websockets.legacy.server',
        'websockets.legacy.client',
        'websockets.legacy.protocol',
        'websockets.asyncio',
        'websockets.asyncio.server',
        'websockets.asyncio.client',
        
        # Media / vision
        'mss',
        'mss.windows',
        'cv2',
        'numpy',
        'PIL',
        'PIL.Image',
        
        # Input simulation
        'pynput',
        'pynput.keyboard',
        'pynput.keyboard._win32',
        'pynput.mouse',
        'pynput.mouse._win32',
        'pynput._util',
        'pynput._util.win32',
        'vgamepad',
        
        # Audio (Windows)
        'pycaw',
        'pycaw.pycaw',
        'comtypes',
        'comtypes.client',
        
        # System info / clipboard
        'psutil',
        'pyperclip',
        
        # Logging / web
        'loguru',
        'qrcode',
        
        # Crypto
        'cryptography',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.asymmetric',
        'cryptography.hazmat.primitives.asymmetric.rsa',
        'cryptography.hazmat.primitives.serialization',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.backends',
        'cryptography.x509',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Linux/Mac-only modules that generate useless warnings
        'evdev',
        'libevdev',
        'Xlib',
        'AppKit',
        'Quartz',
        'CoreFoundation',
        'HIServices',
        'objc',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NexRemote',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,               # GUI-only (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/assets/images/logo.ico',
)
