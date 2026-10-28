"""Exclusive UTF-8 candidate creation without following directory redirects.

POSIX pins directory ancestry with directory FDs and O_NOFOLLOW. Windows pins
every directory with read-attributes handles that deny write/delete sharing,
rejects reparse points, and uses CREATE_NEW for the leaf. Sharing conflicts
fail closed; this helper never retries with weaker flags. Windows UNC/network
roots are unsupported. The Windows implementation requires native validation.

Success means all bytes were written and flushed. Failure may leave newly
created directories or an incomplete *new* candidate; no cleanup removes or
overwrites a possibly concurrently replaced file. POSIX FDs prevent symlink
redirection but cannot prohibit another process from renaming an opened inode.
An observed ancestry change raises OSError, including after creation.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import errno
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import unicodedata


def _parts(value: str) -> tuple[str, ...]:
    if not isinstance(value, str):
        raise ValueError("Candidate path must be a relative string.")
    value = value.replace("\\", "/")
    parts = tuple(value.split("/"))
    if not value or any(unicodedata.category(c).startswith("C") for c in value):
        raise ValueError("Candidate path must be nonempty and contain no controls.")
    for part in parts:
        if (part in {"", ".", ".."} or any(c in part for c in ':*?"<>|')
                or part.endswith((".", " "))
                or re.fullmatch(r"(?:con|prn|aux|nul|conin\$|conout\$|com[0-9¹²³]|lpt[0-9¹²³])(?:\..*)?", part, re.I)):
            raise ValueError("Candidate path must be a portable project-relative file path.")
    return parts


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _verify_posix(chain: list[tuple[int, str, int]]) -> None:
    for parent, name, child in chain:
        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode) or _identity(info) != _identity(os.fstat(child)):
            raise OSError(errno.ESTALE, "Candidate directory ancestry changed.")


def _create_posix(root: Path, parts: tuple[str, ...], data: bytes) -> None:
    if (not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY")
            or os.open not in os.supports_dir_fd or os.mkdir not in os.supports_dir_fd
            or os.stat not in os.supports_dir_fd or os.stat not in os.supports_follow_symlinks):
        raise NotImplementedError("Candidate creation requires no-follow directory-FD operations.")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    handles: list[int] = []
    chain: list[tuple[int, str, int]] = []
    leaf = None
    try:
        handles.append(os.open(root.anchor, flags))
        # Open existing project ancestry first; never create the project root.
        for name in root.parts[1:]:
            child = os.open(name, flags, dir_fd=handles[-1])
            chain.append((handles[-1], name, child))
            handles.append(child)
        for name in parts[:-1]:
            try:
                os.mkdir(name, mode=0o700, dir_fd=handles[-1])
            except FileExistsError:
                pass
            child = os.open(name, flags, dir_fd=handles[-1])
            chain.append((handles[-1], name, child))
            handles.append(child)
        _verify_posix(chain)
        leaf = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                       | getattr(os, "O_CLOEXEC", 0), 0o600, dir_fd=handles[-1])
        if not stat.S_ISREG(os.fstat(leaf).st_mode):
            raise OSError(errno.EINVAL, "Candidate is not a regular file.")
        _verify_posix(chain)
        view = memoryview(data)
        while view:
            written = os.write(leaf, view[:65536])
            if written <= 0:
                raise OSError(errno.EIO, "Candidate write made no progress.")
            view = view[written:]
        os.fsync(leaf)
        _verify_posix(chain)
        named = os.stat(parts[-1], dir_fd=handles[-1], follow_symlinks=False)
        if not stat.S_ISREG(named.st_mode) or _identity(named) != _identity(os.fstat(leaf)):
            raise OSError(errno.ESTALE, "Candidate file was replaced while writing.")
    finally:
        if leaf is not None:
            os.close(leaf)
        for handle in reversed(handles):
            os.close(handle)


class _FileInformation(ctypes.Structure):
    _fields_ = [
        ("attributes", wintypes.DWORD), ("created", wintypes.FILETIME),
        ("accessed", wintypes.FILETIME), ("written", wintypes.FILETIME),
        ("volume", wintypes.DWORD), ("size_high", wintypes.DWORD),
        ("size_low", wintypes.DWORD), ("links", wintypes.DWORD),
        ("index_high", wintypes.DWORD), ("index_low", wintypes.DWORD),
    ]


class _WindowsAPI:
    """Small Win32 adapter; imported API is used only on native Windows."""

    def __init__(self) -> None:
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateFileW": ([wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                             wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE], wintypes.HANDLE),
            "CreateDirectoryW": ([wintypes.LPCWSTR, wintypes.LPVOID], wintypes.BOOL),
            "GetDriveTypeW": ([wintypes.LPCWSTR], wintypes.UINT),
            "GetFileInformationByHandle": ([wintypes.HANDLE, ctypes.POINTER(_FileInformation)], wintypes.BOOL),
            "GetFileType": ([wintypes.HANDLE], wintypes.DWORD),
            "WriteFile": ([wintypes.HANDLE, wintypes.LPCVOID, wintypes.DWORD,
                           ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID], wintypes.BOOL),
            "FlushFileBuffers": ([wintypes.HANDLE], wintypes.BOOL),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = arguments, result

    def _open(self, path: str, *, directory: bool) -> int:
        # Directories: FILE_READ_ATTRIBUTES, FILE_SHARE_READ only, OPEN_EXISTING.
        # Denying WRITE as well as DELETE also prevents reparse mutation through
        # another write handle. Existing incompatible handles cause failure.
        access, sharing, disposition = (0x80, 1, 3) if directory else (0x40000080, 0, 1)
        flags = 0x00200000 | (0x02000000 if directory else 0x80)
        handle = self.kernel.CreateFileW(path, access, sharing, None, disposition, flags, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            info = _FileInformation()
            if not self.kernel.GetFileInformationByHandle(handle, ctypes.byref(info)):
                raise ctypes.WinError(ctypes.get_last_error())
            if (info.attributes & 0x400 or bool(info.attributes & 0x10) != directory
                    or self.kernel.GetFileType(handle) != 1):
                raise OSError(errno.EINVAL, "Candidate path contains a reparse point or unexpected file type.")
            return handle
        except BaseException:
            self.close(handle)
            raise

    def pin(self, path: str) -> int:
        return self._open(path, directory=True)

    def require_local_drive(self, anchor: str) -> None:
        if self.kernel.GetDriveTypeW(anchor) not in {2, 3, 6}:
            raise ValueError("Candidate creation requires a local removable, fixed or RAM drive.")

    def mkdir(self, path: str) -> None:
        if not self.kernel.CreateDirectoryW(path, None):
            error = ctypes.get_last_error()
            if error != 183:  # ERROR_ALREADY_EXISTS; pin() still checks its type.
                raise ctypes.WinError(error)

    def create(self, path: str) -> int:
        return self._open(path, directory=False)

    def write(self, handle: int, data: bytes) -> None:
        for offset in range(0, len(data), 65536):
            chunk = data[offset:offset+65536]
            while chunk:
                count = wintypes.DWORD()
                buffer = ctypes.create_string_buffer(chunk)
                if not self.kernel.WriteFile(handle, buffer, len(chunk), ctypes.byref(count), None):
                    raise ctypes.WinError(ctypes.get_last_error())
                if not 0 < count.value <= len(chunk):
                    raise OSError(errno.EIO, "Candidate write made no progress.")
                chunk = chunk[count.value:]
        if not self.kernel.FlushFileBuffers(handle):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self, handle: int) -> None:
        self.kernel.CloseHandle(handle)


def _create_windows(root: str, parts: tuple[str, ...], data: bytes) -> None:
    project = PureWindowsPath(root)
    if not re.fullmatch(r"[a-zA-Z]:", project.drive) or not project.root:
        raise ValueError("Candidate creation requires a local absolute Windows drive path; UNC roots are unsupported.")
    if any(part in {".", ".."} for part in project.parts):
        raise ValueError("Project root cannot contain traversal.")
    api = _WindowsAPI()
    api.require_local_drive(project.anchor)
    handles: list[int] = []
    leaf = None
    current = PureWindowsPath(project.anchor)
    # Extended path spelling avoids Win32 trailing-dot/space and MAX_PATH aliases.
    native = lambda path: "\\\\?\\" + str(path)
    try:
        handles.append(api.pin(native(current)))
        for part in project.parts[1:]:
            current /= part
            handles.append(api.pin(native(current)))
        for part in parts[:-1]:
            current /= part
            api.mkdir(native(current))
            handles.append(api.pin(native(current)))
        leaf = api.create(native(current / parts[-1]))
        api.write(leaf, data)
    finally:
        if leaf is not None:
            api.close(leaf)
        for handle in reversed(handles):
            api.close(handle)


def create_candidate(root: Path, relative_path: str, content: str) -> None:
    """Create one new UTF-8 candidate, optionally creating project subdirectories.

    Invalid paths raise ValueError; existing leaves raise FileExistsError or a
    platform-specific OSError. Unsafe ancestry, sharing conflicts and I/O failures raise
    OSError. No existing file is overwritten. Unsupported no-follow backends
    raise NotImplementedError. The supplied project root must already exist.
    """
    parts = _parts(relative_path)
    if not isinstance(content, str):
        raise TypeError("Candidate content must be a string.")
    data = content.encode("utf-8")
    project = Path(root).absolute()
    if ".." in project.parts:
        raise ValueError("Project root cannot contain traversal.")
    if os.name == "nt":
        _create_windows(str(project), parts, data)
    elif os.name == "posix":
        _create_posix(project, parts, data)
    else:
        raise NotImplementedError("Candidate creation is unsupported on this platform.")


__all__ = ["create_candidate"]
