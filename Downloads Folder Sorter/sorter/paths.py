from __future__ import annotations

import ctypes
import os
from pathlib import Path

KNOWN_FOLDER_IDS = {
    "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
    "desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
    "pictures": "{33E28130-4E1E-4676-835A-98395C3BC3BB}",
    "videos": "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}",
}


def known_folder_path(folder_name: str, fallback: Path) -> Path:
    if os.name != "nt":
        return fallback

    folder_id = KNOWN_FOLDER_IDS[folder_name]

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", ctypes.c_ulong),
            ("Data2", ctypes.c_ushort),
            ("Data3", ctypes.c_ushort),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    shell32 = ctypes.windll.shell32
    ole32 = ctypes.windll.ole32
    guid = GUID()
    path_pointer = ctypes.c_void_p()

    if ole32.CLSIDFromString(folder_id, ctypes.byref(guid)) != 0:
        return fallback

    result = shell32.SHGetKnownFolderPath(
        ctypes.byref(guid),
        0,
        None,
        ctypes.byref(path_pointer),
    )
    if result != 0:
        return fallback

    try:
        return Path(ctypes.wstring_at(path_pointer.value))
    finally:
        ole32.CoTaskMemFree(path_pointer)


def resolve_path(path_text: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path_text))).resolve()


def is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
