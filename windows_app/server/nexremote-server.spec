# PyInstaller spec: onedir build of the NexRemote host sidecar.
# Build: uv run pyinstaller nexremote-server.spec --noconfirm   ->  dist/nexremote-server/
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("websockets")
    + collect_submodules("winrt")
    + collect_submodules("nexremote_server")
    + ["win32timezone", "pycaw.pycaw", "comtypes.stream"]
)
datas = collect_data_files("vgamepad") + collect_data_files("winrt")
binaries = collect_dynamic_libs("vgamepad") + collect_dynamic_libs("pyaudiowpatch") + collect_dynamic_libs("simplejpeg")

a = Analysis(
    ["src/nexremote_server/__main__.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "pytest", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="nexremote-server",
    console=False,  # no console window; Electron reads stdout through a pipe
    disable_windowed_traceback=False,
    icon="../desktop/build/icon.ico",
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="nexremote-server")
