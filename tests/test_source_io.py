"""Synthetic exclusive writes, deterministic races and Win32 contract checks."""

from __future__ import annotations

import ctypes
import errno
import os
from pathlib import Path
import subprocess
import sys

import pytest

from flg.core import source_io as module
from flg.core.source_io import create_candidate, descriptor_signature


@pytest.fixture
def project(tmp_path):
    # Do not accidentally test through a host's temporary-directory alias.
    root = tmp_path.resolve() / "project"
    root.mkdir()
    return root


def test_new_parents_and_exact_utf8_bytes(project):
    content = '{"review":"合成材料"}\r\n' + "large synthetic block\n" * 10000
    assert create_candidate(project, "new/reviews/candidate.json", content) is None
    assert (project / "new/reviews/candidate.json").read_bytes() == content.encode("utf-8")
    if os.name == "posix":
        assert (project / "new/reviews/candidate.json").stat().st_mode & 0o777 == 0o600


def test_empty_content_and_windows_relative_separators(project):
    create_candidate(project, "nested\\empty.json", "")
    assert (project / "nested/empty.json").read_bytes() == b""


@pytest.mark.parametrize("relative", [
    "", ".", "..", "./file.json", "../file.json", "a/../file.json", "/file.json",
    "a//file.json", "a/./file.json", "a/", "C:/file.json", "C:file.json",
    "\\\\host\\share\\file.json", "\\file.json", "file:stream", "file\x00.json",
    "a\n/file.json", "a\u202e/file.json", "name./file.json", "name /file.json",
    "nul", "CON.json", "COM1.json", "LPT¹", "CONIN$", "CONOUT$",
    "a?.json", "a*.json", 'a".json', "a|.json",
])
def test_invalid_paths_have_no_side_effects(project, relative):
    with pytest.raises(ValueError):
        create_candidate(project, relative, "synthetic")
    assert list(project.iterdir()) == []


@pytest.mark.parametrize("content", [None, b"bytes", 42])
def test_non_string_content_is_rejected_before_creation(project, content):
    with pytest.raises(TypeError):
        create_candidate(project, "new/candidate.json", content)
    assert list(project.iterdir()) == []


def test_bad_unicode_is_rejected_before_creation(project):
    with pytest.raises(UnicodeEncodeError):
        create_candidate(project, "new/candidate.json", "\ud800")
    assert list(project.iterdir()) == []


@pytest.mark.parametrize("kind", ["file", "directory", "symlink"])
def test_existing_leaf_never_overwritten(project, kind):
    leaf = project / "candidate.json"
    original = project / "original.json"
    original.write_text("keep original", encoding="utf-8")
    if kind == "file":
        leaf.write_text("keep candidate", encoding="utf-8")
    elif kind == "directory":
        leaf.mkdir()
    else:
        try:
            leaf.symlink_to(original)
        except OSError:
            pytest.skip("Host cannot create symlinks")
    with pytest.raises(OSError):
        create_candidate(project, "candidate.json", "replace")
    assert original.read_text(encoding="utf-8") == "keep original"
    if kind == "file":
        assert leaf.read_text(encoding="utf-8") == "keep candidate"


def test_symlinked_directory_and_root_ancestry_are_rejected(project):
    outside = project.parent / "outside"
    outside.mkdir()
    link = project / "redirect"
    try:
        link.symlink_to(outside, target_is_directory=True)
        (project.parent / "root-alias").symlink_to(project, target_is_directory=True)
    except OSError:
        pytest.skip("Host cannot create symlinks")
    for root, relative in [
        (project, "redirect/nested/candidate.json"),
        (project.parent / "root-alias", "candidate.json"),
        (project.parent / "root-alias" / "nested", "candidate.json"),
    ]:
        with pytest.raises(OSError):
            create_candidate(root, relative, "synthetic")
    assert list(outside.iterdir()) == []


def test_missing_project_is_not_created(project):
    missing = project / "missing-project"
    with pytest.raises(FileNotFoundError):
        create_candidate(missing, "new/candidate.json", "synthetic")
    assert not missing.exists()


def test_two_processes_cannot_overwrite_each_other(project):
    program = """
import sys
from pathlib import Path
from flg.core.source_io import create_candidate
try:
    create_candidate(Path(sys.argv[1]), 'candidate.json', sys.argv[2])
except OSError:
    print('refused')
else:
    print('created')
"""
    environment = dict(os.environ, PYTHONPATH=str(Path(module.__file__).resolve().parents[2]))
    processes = [subprocess.Popen([sys.executable, "-c", program, str(project), value],
                                 env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True) for value in ["first synthetic candidate", "second synthetic candidate"]]
    outputs = [process.communicate(timeout=20) for process in processes]
    assert all(process.returncode == 0 for process in processes), outputs
    assert sorted(output.strip() for output, _ in outputs) == ["created", "refused"]
    assert (project / "candidate.json").read_text(encoding="utf-8") in {
        "first synthetic candidate", "second synthetic candidate"}


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO")
def test_fifo_leaf_is_not_opened_or_overwritten(project):
    os.mkfifo(project / "candidate.json")
    with pytest.raises(FileExistsError):
        create_candidate(project, "candidate.json", "synthetic")


def wrap_open(monkeypatch, replacement):
    monkeypatch.setattr(os, "open", replacement)
    monkeypatch.setattr(os, "supports_dir_fd", os.supports_dir_fd | {replacement})


@pytest.mark.skipif(os.name != "posix", reason="POSIX FD races")
@pytest.mark.parametrize("moment", ["before_pin", "before_create"])
def test_parent_replacement_race_never_writes_through_symlink(project, monkeypatch, moment):
    parent = project / "output"
    parent.mkdir()
    outside = project.parent / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.json"
    sentinel.write_bytes(b"outside stays unchanged")
    original = os.open
    swapped = False
    def racing_open(path, flags, *args, **kwargs):
        nonlocal swapped
        trigger = (path == "output" and bool(flags & os.O_DIRECTORY) if moment == "before_pin"
                   else path == "candidate.json" and bool(flags & os.O_CREAT))
        if trigger and not swapped:
            swapped = True
            parent.rename(project / "held-output")
            parent.symlink_to(outside, target_is_directory=True)
        return original(path, flags, *args, **kwargs)
    wrap_open(monkeypatch, racing_open)
    with pytest.raises(OSError):
        create_candidate(project, "output/candidate.json", "must not leave project")
    assert swapped
    assert sorted(p.name for p in outside.iterdir()) == ["sentinel.json"]
    assert sentinel.read_bytes() == b"outside stays unchanged"
    # The fixed FD may create an empty file in the original, renamed parent;
    # the helper detects the changed route and never claims success.
    if moment == "before_create":
        assert (project / "held-output/candidate.json").read_bytes() == b""


@pytest.mark.skipif(os.name != "posix", reason="POSIX leaf race")
def test_leaf_replaced_during_write_is_detected_without_touching_replacement(project, monkeypatch):
    outside = project.parent / "outside.json"
    outside.write_bytes(b"unchanged")
    original = os.write
    swapped = False
    def racing_write(fd, data):
        nonlocal swapped
        result = original(fd, data)
        if not swapped:
            swapped = True
            (project / "candidate.json").rename(project / "held.json")
            (project / "candidate.json").symlink_to(outside)
        return result
    monkeypatch.setattr(os, "write", racing_write)
    with pytest.raises(OSError):
        create_candidate(project, "candidate.json", "synthetic")
    assert outside.read_bytes() == b"unchanged"
    assert (project / "candidate.json").is_symlink()
    assert (project / "held.json").read_bytes() == b"synthetic"


@pytest.mark.skipif(os.name != "posix", reason="POSIX short writes")
def test_short_writes_are_completed(project, monkeypatch):
    original = os.write
    monkeypatch.setattr(os, "write", lambda fd, data: original(fd, data[:3]))
    create_candidate(project, "candidate.json", "合成 short write test")
    assert (project / "candidate.json").read_text(encoding="utf-8") == "合成 short write test"


@pytest.mark.skipif(os.name != "posix", reason="POSIX error injection")
def test_failed_write_does_not_report_success_or_delete_anything(project, monkeypatch):
    protected = project / "other.json"
    protected.write_bytes(b"keep")
    monkeypatch.setattr(os, "write", lambda *args: 0)
    with pytest.raises(OSError, match="no progress"):
        create_candidate(project, "candidate.json", "synthetic")
    assert protected.read_bytes() == b"keep"
    assert (project / "candidate.json").read_bytes() == b""


@pytest.mark.skipif(os.name != "posix", reason="POSIX descriptor accounting")
def test_all_opened_descriptors_close_on_failure(project, monkeypatch):
    original = os.open
    opened = []
    def track(*args, **kwargs):
        fd = original(*args, **kwargs)
        opened.append(fd)
        return fd
    wrap_open(monkeypatch, track)
    monkeypatch.setattr(os, "write", lambda *args: 0)
    with pytest.raises(OSError):
        create_candidate(project, "nested/candidate.json", "synthetic")
    assert opened
    for fd in opened:
        with pytest.raises(OSError) as error:
            os.fstat(fd)
        assert error.value.errno == errno.EBADF


@pytest.mark.skipif(os.name != "posix", reason="POSIX capability guard")
def test_missing_nofollow_capabilities_fail_closed(project, monkeypatch):
    monkeypatch.setattr(os, "supports_dir_fd", set())
    with pytest.raises(NotImplementedError):
        create_candidate(project, "candidate.json", "synthetic")
    assert list(project.iterdir()) == []


class Function:
    """Win32 contract shim; does not claim native Windows behavior."""
    def __init__(self, call):
        self.call = call
    def __call__(self, *args):
        return self.call(*args)


class Kernel:
    def __init__(self, *, reparse=None, error=None, drive_type=3):
        self.opens, self.closed, self.data, self.directories = [], [], bytearray(), []
        self.attributes = {}
        self.error = error
        self.CreateFileW = Function(self.open)
        self.CreateDirectoryW = Function(lambda path, security: self.directories.append(path) or 1)
        self.GetDriveTypeW = Function(lambda anchor: drive_type)
        self.GetFileInformationByHandle = Function(self.info)
        self.GetFileType = Function(lambda handle: 1)
        self.WriteFile = Function(self.write)
        self.FlushFileBuffers = Function(lambda handle: 1)
        self.CloseHandle = Function(lambda handle: self.closed.append(handle) or 1)
        self.reparse = reparse
    def open(self, path, access, sharing, security, disposition, flags, template):
        self.opens.append((path, access, sharing, disposition, flags))
        if self.error and path.endswith(self.error):
            return ctypes.c_void_p(-1).value
        handle = len(self.opens)
        self.attributes[handle] = (0x10 if flags & 0x02000000 else 0) | (
            0x400 if self.reparse and path.endswith(self.reparse) else 0)
        return handle
    def info(self, handle, pointer):
        ctypes.cast(pointer, ctypes.POINTER(module._FileInformation)).contents.attributes = self.attributes[handle]
        return 1
    def write(self, handle, buffer, size, pointer, overlapped):
        count = min(size, 17)  # Exercise Win32 short-write handling too.
        self.data.extend(ctypes.string_at(buffer, count))
        ctypes.cast(pointer, ctypes.POINTER(module.wintypes.DWORD)).contents.value = count
        return 1


def windows_shim(monkeypatch, kernel):
    monkeypatch.setattr(ctypes, "WinDLL", lambda *args, **kwargs: kernel, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 183, raising=False)
    monkeypatch.setattr(ctypes, "WinError", lambda code: FileExistsError(errno.EEXIST, "Synthetic Win32 error"), raising=False)


def test_windows_handle_contract_pins_ancestors_and_denies_write_delete_sharing(monkeypatch):
    kernel = Kernel()
    windows_shim(monkeypatch, kernel)
    data = "合成 candidate\r\n".encode("utf-8")
    module._create_windows("Q:/synthetic/project", ("new", "candidate.json"), data)
    assert bytes(kernel.data) == data
    assert len(kernel.opens) == 5  # drive root, synthetic, project, new, file
    for path, access, sharing, disposition, flags in kernel.opens[:-1]:
        assert path.startswith("\\\\?\\Q:\\")
        assert access == 0x81  # LIST_DIRECTORY must participate in share checks.
        assert sharing == 1  # READ only; never WRITE(2) or DELETE(4).
        assert disposition == 3  # OPEN_EXISTING
        assert flags & 0x00200000 and flags & 0x02000000
    _, access, sharing, disposition, flags = kernel.opens[-1]
    assert access == 0x40000080 and sharing == 0 and disposition == 1
    assert flags & 0x00200000  # CREATE_NEW plus OPEN_REPARSE_POINT
    assert kernel.closed == [5, 4, 3, 2, 1]


def test_windows_reparse_fails_before_leaf_creation_and_closes_handles(monkeypatch):
    kernel = Kernel(reparse="redirect")
    windows_shim(monkeypatch, kernel)
    with pytest.raises(OSError, match="reparse"):
        module._create_windows("Q:/project", ("redirect", "candidate.json"), b"synthetic")
    assert all(not row[0].endswith("candidate.json") for row in kernel.opens)
    assert sorted(kernel.closed) == [1, 2, 3]
    assert kernel.data == b""


def test_windows_existing_leaf_fails_without_fallback_or_handle_leak(monkeypatch):
    kernel = Kernel(error="candidate.json")
    windows_shim(monkeypatch, kernel)
    with pytest.raises(FileExistsError):
        module._create_windows("Q:/project", ("candidate.json",), b"synthetic")
    assert len(kernel.opens) == 3
    assert kernel.closed == [2, 1]
    assert kernel.data == b""


def test_descriptor_signature_matches_two_descriptors_and_preserves_position(project):
    path = project / "source.txt"
    path.write_bytes(b"synthetic")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    first, second = os.open(path, flags), os.open(path, flags)
    try:
        os.lseek(first, 3, os.SEEK_SET)
        signature = descriptor_signature(first)
        assert signature == descriptor_signature(second)
        assert os.lseek(first, 0, os.SEEK_CUR) == 3
        if os.name == "nt":
            assert len(signature) == 4
            assert signature[2] == len(b"synthetic")
        else:
            info = os.fstat(first)
            assert signature == (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        path.write_bytes(b"synthetic updated")
        assert descriptor_signature(first) != signature
    finally:
        os.close(second)
        os.close(first)


def test_windows_descriptor_signature_uses_native_handle_and_full_precision(monkeypatch):
    from types import SimpleNamespace

    kernel = Kernel()
    windows_shim(monkeypatch, kernel)
    handles = []
    def info(handle, pointer):
        handles.append(handle)
        result = ctypes.cast(pointer, ctypes.POINTER(module._FileInformation)).contents
        result.volume = 123
        result.index_high, result.index_low = 7, 0xABCDEF01
        result.size_high, result.size_low = 2, 0xFEDCBA98
        result.written.dwHighDateTime, result.written.dwLowDateTime = 0x1234567, 0x89ABCDEF
        return 1
    kernel.GetFileInformationByHandle = Function(info)
    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(get_osfhandle=lambda fd: 4321 if fd == 91 else -1))
    def unexpected(*args):
        pytest.fail("Native signatures must not consult CRT fstat")
    with monkeypatch.context() as local:
        local.setattr(os, "fstat", unexpected)
        signature = module._windows_descriptor_signature(91)
    assert signature == (
        123, (7 << 32) | 0xABCDEF01, (2 << 32) | 0xFEDCBA98,
        (0x1234567 << 32) | 0x89ABCDEF,
    )
    assert handles == [4321]
    assert kernel.opens == [] and kernel.closed == []  # Borrowed, not owned.


@pytest.mark.parametrize("drive_type", [0, 1, 4, 5])
def test_windows_remote_or_unknown_drives_are_rejected_before_creation(monkeypatch, drive_type):
    kernel = Kernel(drive_type=drive_type)
    windows_shim(monkeypatch, kernel)
    with pytest.raises(ValueError, match="local"):
        module._create_windows("Q:/project", ("candidate.json",), b"synthetic")
    assert kernel.opens == [] and kernel.directories == []


@pytest.mark.parametrize("root", ["Q:relative", "relative", "\\\\server\\share\\project", "\\\\?\\C:\\project"])
def test_windows_unsupported_root_spellings_fail_closed(root):
    with pytest.raises(ValueError):
        module._create_windows(root, ("candidate.json",), b"synthetic")


@pytest.mark.skipif(os.name != "nt", reason="Native Windows rename denial requires Windows")
def test_native_windows_pinned_parent_cannot_be_renamed(project, monkeypatch):
    parent = project / "output"
    parent.mkdir()
    original = module._WindowsAPI.create
    checked = False
    def racing_create(api, path):
        nonlocal checked
        with pytest.raises(PermissionError):
            parent.rename(project / "held-output")
        checked = True
        return original(api, path)
    monkeypatch.setattr(module._WindowsAPI, "create", racing_create)
    create_candidate(project, "output/candidate.json", "synthetic")
    assert checked
    assert (parent / "candidate.json").read_bytes() == b"synthetic"


@pytest.mark.skipif(os.name != "nt", reason="Native Windows junction requires Windows")
def test_native_windows_junction_is_rejected(project):
    outside = project.parent / "outside"
    outside.mkdir()
    link = project / "redirect"
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True)
    if result.returncode:
        pytest.skip("Host cannot create junctions")
    with pytest.raises(OSError):
        create_candidate(project, "redirect/candidate.json", "synthetic")
    assert list(outside.iterdir()) == []
