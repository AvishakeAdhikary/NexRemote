"""File explorer. Reply shapes match the legacy host exactly."""

from __future__ import annotations

import asyncio
import ctypes
import os
import shutil
import string
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from nexremote_server.features.base import Feature
from nexremote_server.protocol.jsonutil import get_str

MAX_READ_BYTES = 5 * 1024 * 1024
_DRIVE_KINDS = {
    0: "unknown",
    1: "norootdirectory",
    2: "removable",
    3: "fixed",
    4: "network",
    5: "cdrom",
    6: "ram",
}


def _error(message: str) -> dict[str, Any]:
    return {"type": "file_explorer", "action": "error", "message": message}


def _fmt(ts: float, seconds: bool = False) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S" if seconds else "%Y-%m-%d %H:%M")


def drive_roots() -> list[str]:
    if sys.platform != "win32":
        return ["/"]
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    return [f"{letter}:\\" for i, letter in enumerate(string.ascii_uppercase) if mask & (1 << i)]


def _drive_info(root: str) -> dict[str, Any]:
    kind, label, ready = "fixed", "", True
    if sys.platform == "win32":
        k32 = ctypes.windll.kernel32
        kind = _DRIVE_KINDS.get(k32.GetDriveTypeW(root), "unknown")
        buf = ctypes.create_unicode_buffer(261)
        old_mode = k32.SetErrorMode(1)  # SEM_FAILCRITICALERRORS: no "insert disk" dialogs
        try:
            ready = bool(k32.GetVolumeInformationW(root, buf, 261, None, None, None, None, 0))
        finally:
            k32.SetErrorMode(old_mode)
        label = buf.value if ready else ""
    return {"name": root, "path": root, "kind": kind, "is_ready": ready, "label": label}


def validate_path(path: str) -> bool:
    if not path or not path.strip():
        return False
    try:
        resolved = os.path.abspath(path).lower()
    except (OSError, ValueError):
        return False
    return any(resolved.startswith(os.path.abspath(root).lower()) for root in drive_roots())


def _entry(path: str) -> dict[str, Any]:
    st = os.stat(path)
    is_dir = os.path.isdir(path)
    item: dict[str, Any] = {"name": os.path.basename(path), "path": path, "is_directory": is_dir}
    if not is_dir:
        item["size"] = st.st_size  # omitted for directories (legacy wrote no null)
    item["modified"] = _fmt(st.st_mtime)
    return item


def _sorted(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda i: (not i["is_directory"], i["name"].lower()))


def _iter_entries(path: str) -> list[str]:
    with os.scandir(path) as it:
        return [os.path.join(path, e.name) for e in it]


class FileExplorer:
    def handle(self, msg: dict[str, Any]) -> dict[str, Any]:
        action = get_str(msg, "action")
        try:
            match action:
                case "drive_list":
                    return self.drive_list()
                case "list":
                    return self.list_dir(get_str(msg, "path", "C:\\"))
                case "open":
                    return self.open(get_str(msg, "path"))
                case "properties":
                    return self.properties(get_str(msg, "path"))
                case "search":
                    return self.search(get_str(msg, "path", "C:\\"), get_str(msg, "query"))
                case "copy_path":
                    return {"type": "file_explorer", "action": "path_copied", "path": get_str(msg, "path")}
                case "create_folder":
                    return self.create_folder(get_str(msg, "path"), get_str(msg, "name"))
                case "create_file":
                    return self.create_file(
                        get_str(msg, "path"), get_str(msg, "name"), get_str(msg, "content")
                    )
                case "rename":
                    return self.rename(get_str(msg, "path"), get_str(msg, "new_name"))
                case "delete":
                    return self.delete(get_str(msg, "path"))
                case "read_file":
                    return self.read_file(get_str(msg, "path"))
                case "write_file":
                    return self.write_file(get_str(msg, "path"), get_str(msg, "content"))
                case "copy":
                    return self.copy(get_str(msg, "source"), get_str(msg, "destination"))
                case "move":
                    return self.move(get_str(msg, "source"), get_str(msg, "destination"))
                case _:
                    return _error(f"Unknown action: {action}")
        except Exception as exc:  # mirror the legacy catch-all
            return _error(str(exc))

    def drive_list(self) -> dict[str, Any]:
        try:
            drives = sorted((_drive_info(r) for r in drive_roots()), key=lambda d: d["name"])
        except Exception as exc:
            return _error(f"Failed to list drives: {exc}")
        return {"type": "file_explorer", "action": "drive_list", "drives": drives}

    def list_dir(self, path: str) -> dict[str, Any]:
        if not validate_path(path):
            return _error("Invalid or restricted path")
        try:
            items = []
            for entry in _iter_entries(path):
                try:
                    items.append(_entry(entry))
                except OSError:
                    continue  # skip inaccessible entries
        except Exception as exc:
            return _error(f"Failed to list directory: {exc}")
        return {"type": "file_explorer", "action": "list", "path": path, "files": _sorted(items)}

    def open(self, path: str) -> dict[str, Any]:
        if not validate_path(path):
            return _error("Invalid or restricted path")
        try:
            if os.path.isfile(path):
                os.startfile(path)  # type: ignore[attr-defined]
                return {"type": "file_explorer", "action": "file_opened", "path": path}
            if os.path.isdir(path):
                subprocess.Popen(["explorer.exe", path])
                return {"type": "file_explorer", "action": "folder_opened", "path": path}
            return _error("File or folder not found")
        except Exception as exc:
            return _error(f"Failed to open: {exc}")

    def properties(self, path: str) -> dict[str, Any]:
        if not validate_path(path):
            return _error("Invalid or restricted path")
        try:
            if not os.path.exists(path):
                return _error("File or folder not found")
            st = os.stat(path)
            is_dir = os.path.isdir(path)
            return {
                "type": "file_explorer",
                "action": "properties",
                "path": path,
                "name": os.path.basename(path),
                "item_type": "directory" if is_dir else "file",
                "is_directory": is_dir,
                "size": 0 if is_dir else st.st_size,
                "created": _fmt(st.st_birthtime if hasattr(st, "st_birthtime") else st.st_ctime, True),
                "modified": _fmt(st.st_mtime, True),
                "accessed": _fmt(st.st_atime, True),
            }
        except Exception as exc:
            return _error(f"Failed to get properties: {exc}")

    def search(self, path: str, query: str) -> dict[str, Any]:
        if not validate_path(path):
            return _error("Invalid or restricted path")
        try:
            needle = query.lower()
            items = []
            for entry in _iter_entries(path):
                if needle not in os.path.basename(entry).lower():
                    continue
                try:
                    items.append(_entry(entry))
                except OSError:
                    continue
        except Exception as exc:
            return _error(f"Search failed: {exc}")
        return {
            "type": "file_explorer",
            "action": "search",
            "path": path,
            "query": query,
            "files": _sorted(items),
        }

    def create_folder(self, parent: str, name: str) -> dict[str, Any]:
        if not validate_path(parent):
            return _error("Invalid or restricted path")
        new_path = os.path.join(parent, name)
        if os.path.exists(new_path):
            return _error(f'Folder "{name}" already exists')
        try:
            os.makedirs(new_path)
        except FileExistsError:
            return _error(f'Folder "{name}" already exists')
        except Exception as exc:
            return _error(f"Failed to create folder: {exc}")
        return {"type": "file_explorer", "action": "folder_created", "path": new_path, "name": name}

    def create_file(self, parent: str, name: str, content: str) -> dict[str, Any]:
        if not validate_path(parent):
            return _error("Invalid or restricted path")
        new_path = os.path.join(parent, name)
        if os.path.isfile(new_path):
            return _error(f'File "{name}" already exists')
        try:
            Path(new_path).write_text(content or "", encoding="utf-8")
        except Exception as exc:
            return _error(f"Failed to create file: {exc}")
        return {"type": "file_explorer", "action": "file_created", "path": new_path, "name": name}

    def rename(self, path: str, new_name: str) -> dict[str, Any]:
        if not validate_path(path):
            return _error("Invalid or restricted path")
        new_path = os.path.join(os.path.dirname(path), new_name)
        if os.path.exists(new_path):
            return _error(f'"{new_name}" already exists')
        try:
            os.rename(path, new_path)
        except Exception as exc:
            return _error(f"Failed to rename: {exc}")
        return {
            "type": "file_explorer",
            "action": "renamed",
            "old_path": path,
            "new_path": new_path,
            "new_name": new_name,
        }

    def delete(self, path: str) -> dict[str, Any]:
        if not validate_path(path):
            return _error("Invalid or restricted path")
        name = os.path.basename(path)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)
            else:
                return _error("File or folder not found")
        except PermissionError:
            return _error(f'Permission denied: cannot delete "{name}"')
        except Exception as exc:
            return _error(f"Failed to delete: {exc}")
        return {"type": "file_explorer", "action": "deleted", "path": path, "name": name}

    def read_file(self, path: str) -> dict[str, Any]:
        if not validate_path(path):
            return _error("Invalid or restricted path")
        if not os.path.isfile(path):
            return _error("Not a file")
        size = os.path.getsize(path)
        if size > MAX_READ_BYTES:
            return _error(f"File too large ({size} bytes). Max: {MAX_READ_BYTES} bytes")
        try:
            raw = Path(path).read_bytes()
        except PermissionError:
            return _error("Cannot read binary file as text")
        except Exception as exc:
            return _error(f"Failed to read file: {exc}")
        content = _decode_text(raw)
        return {
            "type": "file_explorer",
            "action": "file_content",
            "path": path,
            "name": os.path.basename(path),
            "content": content,
        }

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        if not validate_path(path):
            return _error("Invalid or restricted path")
        try:
            Path(path).write_text(content or "", encoding="utf-8")
        except Exception as exc:
            return _error(f"Failed to write file: {exc}")
        return {
            "type": "file_explorer",
            "action": "file_saved",
            "path": path,
            "name": os.path.basename(path),
            "size": len(content or ""),
        }

    def copy(self, source: str, destination: str) -> dict[str, Any]:
        if not validate_path(source) or not validate_path(destination):
            return _error("Invalid or restricted path")
        target = os.path.join(destination, os.path.basename(source))
        try:
            if os.path.isdir(source):
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                if os.path.exists(target):
                    raise FileExistsError(f"The file '{target}' already exists.")
                shutil.copy2(source, target)
        except Exception as exc:
            return _error(f"Failed to copy: {exc}")
        return {"type": "file_explorer", "action": "copied", "source": source, "destination": target}

    def move(self, source: str, destination: str) -> dict[str, Any]:
        if not validate_path(source) or not validate_path(destination):
            return _error("Invalid or restricted path")
        target = os.path.join(destination, os.path.basename(source))
        try:
            if os.path.exists(target):
                raise FileExistsError(f"The file '{target}' already exists.")
            shutil.move(source, target)
        except Exception as exc:
            return _error(f"Failed to move: {exc}")
        return {"type": "file_explorer", "action": "moved", "source": source, "destination": target}


def _decode_text(raw: bytes) -> str:
    """Decode like .NET File.ReadAllText: honour a BOM, otherwise UTF-8 with replacement."""
    for bom, enc in ((b"\xef\xbb\xbf", "utf-8"), (b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be")):
        if raw.startswith(bom):
            return raw[len(bom) :].decode(enc, errors="replace")
    return raw.decode("utf-8", errors="replace")


class FileExplorerFeature(Feature):
    message_types = ("file_explorer",)

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.explorer = FileExplorer()

    async def handle(self, session, msg_type: str, msg: dict[str, Any]) -> None:
        reply = await asyncio.to_thread(self.explorer.handle, msg)
        await session.send_encrypted(reply)
