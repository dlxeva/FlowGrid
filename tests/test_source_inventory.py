"""Synthetic sources only: discovery, provenance hints and filesystem boundaries."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from flg.core import source_inventory as module
from flg.core.source_inventory import describe, inventory


def put(root, path, content="Synthetic source\n"):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def configured(path="sources/meetings", depth=3, **settings):
    return {"version": 1, "roots": [{"path": path, "max_depth": depth, **settings}]}


def test_defaults_depth_hash_stability_and_no_writes(tmp_path):
    paths = [
        ".flg/sessions/session.md", "docs/meetings/meeting-notes.txt",
        "sources/meetings/a/b/c/transcript.md", "sources/meetings/direct.md",
    ]
    for path in paths:
        put(tmp_path, path, "测试 source\r\n")
    for path in [
        ".flg/sessions/deep/session.md", "docs/meetings/deep/notes.md",
        "sources/meetings/a/b/c/d/notes.md", "unrelated/notes.md",
    ]:
        put(tmp_path, path)
    before = {p.relative_to(tmp_path): (p.read_bytes(), p.stat().st_mtime_ns)
              for p in tmp_path.rglob("*") if p.is_file()}
    result = inventory(tmp_path)
    assert result == inventory(tmp_path)
    assert result["version"] == 1
    assert list(result["files"]) == sorted(paths)
    for path, metadata in result["files"].items():
        assert metadata == describe(tmp_path, path)
        assert metadata["sha256"] == hashlib.sha256((tmp_path / path).read_bytes()).hexdigest()
        assert set(metadata) == {"sha256", "role", "review_eligible", "meeting_id",
                                 "role_basis", "group_basis", "source_roots"}
    after = {p.relative_to(tmp_path): (p.read_bytes(), p.stat().st_mtime_ns)
             for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after


@pytest.mark.parametrize(("name", "role", "review"), [
    ("transcript.md", "transcript", True),
    ("逐字稿.txt", "transcript", True),
    ("转写.md", "transcript", True),
    ("manual_notes.md", "manual_notes", True),
    ("会议纪要.md", "manual_notes", True),
    ("smart-summary.md", "smart_summary", True),
    ("智能纪要.md", "smart_summary", True),
    ("raw_response.md", "raw_response", False),
    ("原始响应.txt", "raw_response", False),
    ("transcript.JSON", "metadata_only", False),
    ("会议纪要.xml", "metadata_only", False),
])
def test_roles_are_hints_and_metadata_is_not_reviewable(tmp_path, name, role, review):
    path = f"sources/meetings/synthetic/{name}"
    put(tmp_path, path, "Not an authorship assertion")
    metadata = describe(tmp_path, path)
    assert metadata["role"] == role
    assert metadata["review_eligible"] is review
    assert metadata["role_basis"] == ("extension" if role == "metadata_only" else "filename_inference")
    assert metadata["meeting_id"] == "sources/meetings/synthetic"
    assert metadata["group_basis"] == "folder"


def test_one_meeting_groups_artifacts_without_corroboration_count(tmp_path):
    paths = [f"sources/meetings/synthetic/{name}" for name in
             ["transcript.md", "智能纪要.txt", "manual_notes.md", "raw_response.md", "details.json"]]
    for path in paths:
        put(tmp_path, path)
    result = inventory(tmp_path)
    assert list(result["meetings"]) == ["sources/meetings/synthetic"]
    meeting = result["meetings"]["sources/meetings/synthetic"]
    assert set(meeting) == {"paths", "review_paths"}
    assert meeting["paths"] == sorted(paths)
    assert meeting["review_paths"] == sorted(p for p in paths if not p.endswith((".json", "raw_response.md")))


def test_custom_roots_replace_defaults_and_explicit_settings(tmp_path):
    put(tmp_path, "docs/meetings/notes.md")
    put(tmp_path, "research/round/transcript.md")
    put(tmp_path, "research/round/data.json")
    config = configured("research\\round", 0, role="smart_summary", meeting_id="synthetic-round")
    result = inventory(tmp_path, config)
    assert list(result["files"]) == ["research/round/data.json", "research/round/transcript.md"]
    metadata = result["files"]["research/round/transcript.md"]
    assert metadata["role"] == "smart_summary"
    assert metadata["role_basis"] == "config"
    assert metadata["group_basis"] == "config"
    assert metadata["meeting_id"] == "synthetic-round"
    assert metadata["source_roots"] == ["research/round"]
    assert result["files"]["research/round/data.json"]["role"] == "metadata_only"
    assert inventory(tmp_path, {"version": 1, "roots": []}) == {"version": 1, "files": {}, "meetings": {}}


@pytest.mark.parametrize("config", [
    {}, [], {"version": True, "roots": []}, {"version": 2, "roots": []},
    {"version": 1, "roots": {}}, {"version": 1, "roots": [], "extra": True},
    {"version": 1, "roots": [None]},
    configured(depth=-1), configured(depth=5), configured(depth=True), configured(depth=1.0),
    configured(role="author"), configured(role=[]), configured(meeting_id=""),
    configured(meeting_id="  "), configured(meeting_id="bad\nidentifier"),
    configured(meeting_id=1), configured(extra=True),
])
def test_invalid_config_raises_before_io(tmp_path, config, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Invalid config must be rejected before filesystem discovery")
    monkeypatch.setattr(module, "_project", unexpected)
    with pytest.raises(ValueError):
        inventory(tmp_path, config)
    with pytest.raises(ValueError):
        describe(tmp_path, "sources/meetings/notes.md", config)


@pytest.mark.parametrize("path", [
    "", ".", "./", "..", "../outside", "sources/../outside", "/outside",
    "C:\\outside", "C:outside", "\\\\server\\share", "\\outside",
    "safe\x00name", "safe\nname", "safe\x7fname", "safe\u202ename",
    "safe//name", "safe/./name", "safe/CON", "safe/nul.txt", "safe/LPT1",
    "safe/name.", "safe/name ", "safe/file:stream", ".git", ".flg",
    "people", "docs/audit", "research/.hidden", "node_modules", "build",
])
def test_unsafe_or_excluded_config_paths(tmp_path, path):
    with pytest.raises(ValueError):
        inventory(tmp_path, configured(path))


@pytest.mark.parametrize("directory", [
    "people", "audit", "cache", "tmp", "temp", ".hidden", "build", "dist",
    "node_modules", "__pycache__", "target", "tmp-scratch", "临时",
])
def test_excluded_subtrees_and_exact_targets(tmp_path, directory):
    hidden = f"sources/meetings/{directory}/transcript.md"
    put(tmp_path, hidden)
    put(tmp_path, "sources/meetings/visible/notes.md")
    assert list(inventory(tmp_path)["files"]) == ["sources/meetings/visible/notes.md"]
    assert describe(tmp_path, hidden) is None


@pytest.mark.parametrize("name", [
    ".hidden.md", "~notes.md", "notes.tmp", "notes.md~", "notes.pdf", "bad\nname.md",
    "notes.tmp.md", "notes-temp.txt",
])
def test_excluded_filenames(tmp_path, name):
    if os.name == "nt" and "\n" in name:
        pytest.skip("Windows does not permit control characters in filenames")
    path = f"sources/meetings/{name}"
    put(tmp_path, path)
    assert inventory(tmp_path)["files"] == {}
    assert describe(tmp_path, path) is None


def test_depth_four_is_exact_and_unknown_filename_is_labeled(tmp_path):
    included = "custom/a/b/c/d/unknown.md"
    put(tmp_path, included)
    put(tmp_path, "custom/a/b/c/d/e/unknown.md")
    result = inventory(tmp_path, configured("custom", 4))
    assert list(result["files"]) == [included]
    assert result["files"][included]["role_basis"] == "fallback_inference"


def test_overlap_merges_provenance_and_hashes_once(tmp_path, monkeypatch):
    path = "sources/meetings/synthetic/transcript.md"
    put(tmp_path, path)
    parent = configured()["roots"][0]
    child = configured("sources/meetings/synthetic", 0)["roots"][0]
    config = {"version": 1, "roots": [parent, child, parent.copy()]}
    calls = []
    original = module._digest
    def track(root, relative):
        calls.append(relative.as_posix())
        return original(root, relative)
    monkeypatch.setattr(module, "_digest", track)
    result = inventory(tmp_path, config)
    assert calls == [path]
    assert result["files"][path]["source_roots"] == ["sources/meetings", "sources/meetings/synthetic"]
    config["roots"].reverse()
    assert inventory(tmp_path, config) == result
    assert describe(tmp_path, path, config) == result["files"][path]


@pytest.mark.parametrize("other", [
    {"path": "sources/meetings", "max_depth": 2},
    {"path": "SOURCES/MEETINGS", "max_depth": 3},
    {"path": "sources/meetings/child", "max_depth": 0, "role": "transcript"},
    {"path": "sources/meetings/child", "max_depth": 0, "meeting_id": "different"},
])
def test_conflicting_declarations_rejected_even_without_files(tmp_path, other):
    config = configured()
    config["roots"].append(other)
    with pytest.raises(ValueError, match="Conflicting"):
        inventory(tmp_path, config)
    config["roots"].reverse()
    with pytest.raises(ValueError, match="Conflicting"):
        describe(tmp_path, "sources/meetings/notes.md", config)


def test_nonintersecting_depth_and_sibling_prefix_are_not_conflicts(tmp_path):
    config = configured(depth=0)
    config["roots"].extend([
        {"path": "sources/meetings/child", "max_depth": 0, "role": "transcript"},
        {"path": "sources/meetings-extra", "max_depth": 0, "meeting_id": "other"},
    ])
    put(tmp_path, "sources/meetings/child/notes.md")
    assert inventory(tmp_path, config)["files"]["sources/meetings/child/notes.md"]["role"] == "transcript"


def test_describe_never_scans_or_reads_siblings(tmp_path, monkeypatch):
    target = "sources/meetings/transcript.md"
    put(tmp_path, target)
    put(tmp_path, "sources/meetings/sibling.md")
    original = os.open
    opens = []
    def track(path, flags, *args, **kwargs):
        if not flags & getattr(os, "O_DIRECTORY", 0):
            opens.append(str(path))
        return original(path, flags, *args, **kwargs)
    def unexpected(*args, **kwargs):
        pytest.fail("describe must not scan")
    monkeypatch.setattr(os, "scandir", unexpected)
    monkeypatch.setattr(os, "open", track)
    assert describe(tmp_path, target) is not None
    assert len(opens) == 2  # Original read + metadata-only verification reopen.
    assert all(path.endswith("transcript.md") for path in opens)
    assert describe(tmp_path, "../outside.md") is None
    assert describe(tmp_path, "unrelated.md") is None
    assert describe(tmp_path, "sources/meetings/missing.md") is None
    assert describe(tmp_path, "sources/meetings") is None


def test_symlink_files_directories_and_declared_roots_are_not_followed(tmp_path):
    put(tmp_path, "outside/notes.md")
    sources = tmp_path / "sources/meetings"
    sources.mkdir(parents=True)
    try:
        (sources / "alias.md").symlink_to(tmp_path / "outside/notes.md")
        (sources / "alias-dir").symlink_to(tmp_path / "outside", target_is_directory=True)
        (tmp_path / "linked-root").symlink_to(sources, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks unavailable")
    assert inventory(tmp_path)["files"] == {}
    assert inventory(tmp_path, configured("linked-root", 4))["files"] == {}
    assert describe(tmp_path, "sources/meetings/alias.md") is None
    assert describe(tmp_path, "sources/meetings/alias-dir/notes.md") is None
    assert describe(tmp_path, "linked-root/notes.md", configured("linked-root")) is None
    with pytest.raises(ValueError, match="symlink"):
        inventory(tmp_path / "linked-root")


def test_portable_fallback_hashes_binary_bytes_without_posix_dir_fds(tmp_path, monkeypatch):
    path = "sources/meetings/synthetic/notes.txt"
    target = put(tmp_path, path)
    target.write_bytes(b"synthetic\r\nsource\x1a\r\n")
    monkeypatch.setattr(os, "supports_dir_fd", set())
    monkeypatch.setattr(os, "supports_fd", set())
    result = describe(tmp_path, path.replace("/", "\\"))
    assert result["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert inventory(tmp_path)["files"][path] == result


def test_windows_reparse_attributes_are_excluded(tmp_path, monkeypatch):
    from types import SimpleNamespace

    path = "sources/meetings/junction/notes.md"
    put(tmp_path, path)
    original = Path.lstat
    def reparse(target, *args, **kwargs):
        info = original(target, *args, **kwargs)
        if target.name == "junction":
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
        return info
    monkeypatch.setattr(Path, "lstat", reparse)
    assert describe(tmp_path, path) is None
    assert inventory(tmp_path)["files"] == {}


@pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"), reason="POSIX directory pinning")
def test_directory_swapped_to_symlink_is_not_scanned(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    put(outside, "private.md")
    source = project / "sources/meetings"
    source.mkdir(parents=True)
    original = module._safe_stat
    swapped = False
    def swap(root, relative):
        nonlocal swapped
        info = original(root, relative)
        if relative.as_posix() == "sources/meetings" and not swapped:
            swapped = True
            source.rename(source.with_name("old-meetings"))
            source.symlink_to(outside, target_is_directory=True)
        return info
    monkeypatch.setattr(module, "_safe_stat", swap)
    assert inventory(project)["files"] == {}


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO test")
def test_device_like_fifo_is_never_opened(tmp_path, monkeypatch):
    path = "sources/meetings/pipe.md"
    (tmp_path / path).parent.mkdir(parents=True)
    os.mkfifo(tmp_path / path)
    def unexpected(*args, **kwargs):
        pytest.fail("FIFO must not be opened")
    monkeypatch.setattr(os, "open", unexpected)
    assert inventory(tmp_path)["files"] == {}
    assert describe(tmp_path, path) is None


@pytest.mark.parametrize(("limit", "value", "message"), [
    ("MAX_ENTRIES", 1, "entry"), ("MAX_FILES", 1, "count"),
    ("MAX_FILE_BYTES", 1, "file byte"), ("MAX_TOTAL_BYTES", 3, "total byte"),
])
def test_budgets_fail_explicitly_without_partial_results(tmp_path, monkeypatch, limit, value, message):
    put(tmp_path, "sources/meetings/a.md", "abc")
    put(tmp_path, "sources/meetings/b.md", "abc")
    monkeypatch.setattr(module, limit, value)
    with pytest.raises(ValueError, match=message):
        inventory(tmp_path)


def test_root_budget_and_missing_project(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "MAX_ROOTS", 1)
    with pytest.raises(ValueError, match="root budget"):
        inventory(tmp_path)
    assert inventory(tmp_path / "missing", configured("custom"))["files"] == {}


def test_unreadable_file_and_concurrent_modification_are_omitted(tmp_path, monkeypatch):
    path = "sources/meetings/notes.md"
    put(tmp_path, path)
    original = os.read
    def changed(fd, count):
        result = original(fd, count)
        if result:
            with (tmp_path / path).open("ab") as stream:
                stream.write(b"changed")
        return result
    # Only mutate once to keep the synthetic adversary bounded.
    calls = 0
    def change_once(fd, count):
        nonlocal calls
        calls += 1
        return changed(fd, count) if calls == 1 else original(fd, count)
    monkeypatch.setattr(os, "read", change_once)
    assert describe(tmp_path, path) is None
    def denied(*args, **kwargs):
        raise PermissionError("Synthetic access failure")
    monkeypatch.setattr(os, "open", denied)
    assert inventory(tmp_path)["files"] == {}


def test_path_stat_and_descriptor_metadata_are_not_mixed(tmp_path, monkeypatch):
    from types import SimpleNamespace

    path = "sources/meetings/synthetic/transcript.md"
    target = put(tmp_path, path, "stable synthetic source")
    original = module._safe_stat
    def unlike_crt(root, relative):
        info = original(root, relative)
        if relative.as_posix() == path and info is not None:
            # Model Python Windows APIs returning different identity/time values
            # for the same unchanged file. Path metadata is only a type/size guard.
            return SimpleNamespace(st_mode=info.st_mode, st_size=info.st_size,
                st_dev=info.st_dev + 1, st_ino=info.st_ino + 2,
                st_mtime_ns=info.st_mtime_ns + 101, st_ctime_ns=info.st_ctime_ns + 202)
        return info
    monkeypatch.setattr(module, "_safe_stat", unlike_crt)
    expected = hashlib.sha256(target.read_bytes()).hexdigest()
    assert describe(tmp_path, path)["sha256"] == expected
    assert inventory(tmp_path)["files"][path]["sha256"] == expected


def test_verification_descriptor_identity_change_is_still_rejected(tmp_path, monkeypatch):
    path = "sources/meetings/synthetic/transcript.md"
    original_path = put(tmp_path, path, "same synthetic bytes")
    replacement = put(tmp_path, "replacement.md", "same synthetic bytes")
    info = original_path.stat()
    os.utime(replacement, ns=(info.st_atime_ns, info.st_mtime_ns))
    original = module._open_source
    count = 0
    def reopen_different_file(root, relative, flags):
        nonlocal count
        count += 1
        if count == 2:
            return os.open(replacement, flags)
        return original(root, relative, flags)
    monkeypatch.setattr(module, "_open_source", reopen_different_file)
    assert describe(tmp_path, path) is None
    assert count == 2  # Same bytes, size and write time must not hide identity drift.


def test_repeated_inventory_never_omits_unchanged_readable_files(tmp_path):
    paths = [f"sources/meetings/synthetic/转写-{index}.md" for index in range(8)]
    for index, path in enumerate(paths):
        put(tmp_path, path, f"合成 source {index}\n")
    baseline = inventory(tmp_path)
    assert list(baseline["files"]) == sorted(paths)
    for _ in range(10):
        assert inventory(tmp_path) == baseline
        for path in paths:
            assert describe(tmp_path, path) == baseline["files"][path]
