"""Synthetic followup tests: no private project input or formal promotion."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256

import pytest
import yaml

from flg.core.capture_followup import collect, record, render_notice


def digest(value):
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


@pytest.fixture
def project(tmp_path):
    folder = tmp_path / ".flg/captures"
    folder.mkdir(parents=True)
    (tmp_path / "DECISIONS.md").write_text("Unchanged formal ledger\n")
    (tmp_path / "WORK.md").write_text("User: experiment checked.\nOther work.\n")
    path = folder / "cap-test.md"
    path.write_text("---\nid: cap-test\nstatus: pending_review\nclaim: Try experiment\nunknown:\n  nested: preserved\n---\n\n# Original body\n\nKeep this exactly.\n")
    return tmp_path, path


def payload(root, disposition="awaiting_evidence", scope="file"):
    quote = "User: experiment checked."
    return {"schema_version": 1, "disposition": disposition, "reason": "Explicit review",
            "waiting_for": ["experiment results"], "review_trigger": "Results arrive",
            "reviewed_at": "2026-10-28T08:00:00Z",
            "refs": [{"path": "WORK.md", "quote": quote, "scope": scope,
                      "sha256": digest(quote if scope == "quote" else (root / "WORK.md").read_bytes())}]}


def save(root, path, data):
    return record(root, "cap-test", data, digest(path.read_bytes()))


def item(root, **kwargs):
    return collect(root, **kwargs)["items"][0]


def test_reads_are_side_effect_free_and_empty(tmp_path, project):
    assert collect(tmp_path / "missing")["total"] == 0
    root, path = project
    before = {p.relative_to(root): (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()}
    assert item(root)["state"] == "unreviewed"
    assert "1 need explicit review" in render_notice(root)
    after = {p.relative_to(root): (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()}
    assert before == after


def test_record_retry_history_body_unknown_no_promotion(project):
    root, path = project
    original_body = path.read_text().split("---\n", 2)[2]
    data = payload(root)
    expected = digest(path.read_bytes())
    first = record(root, "cap-test", data, expected)
    assert first["applied"] and not first["idempotent"]
    raw = path.read_bytes()
    retry = record(root, "cap-test", data, expected)
    assert retry["idempotent"] and not retry["applied"]
    assert path.read_bytes() == raw
    assert first["sha256"] == digest(raw)
    second = save(root, path, payload(root, "absorbed"))
    assert second["applied"]
    meta = yaml.safe_load(path.read_text().split("---\n")[1])
    assert len(meta["followup_history"]) == 2
    assert meta["status"] == "pending_review"
    assert meta["unknown"] == {"nested": "preserved"}
    assert path.read_text().split("---\n", 2)[2] == original_body
    assert (root / "DECISIONS.md").read_text() == "Unchanged formal ledger\n"
    assert not (root / ".flg/.operation.lock").exists()
    assert set(p.name for p in (root / ".flg").iterdir()) == {"captures"}


def test_cas_and_retry_not_for_changed_capture(project):
    root, path = project
    data = payload(root)
    old = digest(path.read_bytes())
    save(root, path, data)
    path.write_text(path.read_text() + "Changed body\n")
    raw = path.read_bytes()
    with pytest.raises(ValueError, match="CAS"):
        record(root, "cap-test", data, old)
    assert path.read_bytes() == raw
    current = item(root)
    assert current["drifted"] and current["claim"] == ""
    assert current["state"] == "needs_review"


def test_waiting_count_notice_and_inclusive_day_due(project):
    root, path = project
    data = payload(root)
    data["review_after"] = "2026-10-29"
    save(root, path, data)
    report = collect(root, now="2026-10-28T23:59:59Z")
    assert report["counts"]["waiting"] == 1
    assert not report["items"][0]["needs_review"]
    due = item(root, now="2026-10-29T00:00:00Z")
    assert due["due"] and due["needs_review"] and due["state"] == "needs_review"
    data.pop("review_after")
    save(root, path, data)
    assert render_notice(root) == ""


@pytest.mark.parametrize("scope,drifted", [("file", True), ("quote", False)])
def test_scope_ignores_unrelated_edits_only_for_quotes(project, scope, drifted):
    root, path = project
    save(root, path, payload(root, "absorbed", scope))
    (root / "WORK.md").write_text("User: experiment checked.\nOther work changed.\n")
    current = item(root)
    assert current["drifted"] is drifted
    assert current["state"] == ("needs_review" if drifted else "absorbed")


@pytest.mark.parametrize("replacement", ["Different quote", "User: experiment checked.\nUser: experiment checked."])
def test_missing_or_ambiguous_quote_reopens(project, replacement):
    root, path = project
    save(root, path, payload(root, "rejected", "quote"))
    (root / "WORK.md").write_text(replacement)
    assert item(root)["state"] == "needs_review"
    assert item(root)["claim"] == ""


@pytest.mark.parametrize("change", [
    {"waiting_for": []}, {"review_trigger": ""}, {"disposition": "absorbed", "refs": []},
    {"disposition": "expired", "reason": ""}, {"reviewed_at": "not-a-date"},
    {"review_after": "yesterday"}, {"disposition": "confirmed"}, {"schema_version": True},
    {"refs": [{"path": "WORK.md", "quote": "User: experiment checked."}]},
])
def test_invalid_metadata_does_not_write(project, change):
    root, path = project
    data = payload(root)
    data.update(change)
    raw = path.read_bytes()
    with pytest.raises(ValueError):
        save(root, path, data)
    assert path.read_bytes() == raw


@pytest.mark.parametrize("refpath", ["../outside.md", "/etc/passwd", ".flg/../WORK.md", "WORK\\bad.md"])
def test_unsafe_refs_rejected(project, refpath):
    root, path = project
    data = payload(root)
    data["refs"][0]["path"] = refpath
    with pytest.raises(ValueError):
        save(root, path, data)


def test_symlink_capture_refs_and_parent_rejected(project):
    root, path = project
    ref = root / "link.md"
    ref.symlink_to(root / "WORK.md")
    data = payload(root)
    data["refs"][0]["path"] = "link.md"
    with pytest.raises(ValueError, match="Symlink"):
        save(root, path, data)
    alias = root / "alias"
    alias.symlink_to(root, target_is_directory=True)
    assert collect(alias)["errors"]
    symlink = path.parent / "cap-link.md"
    symlink.symlink_to(path)
    assert collect(root)["errors"]
    with pytest.raises(ValueError):
        record(root, "../cap-test", data, digest(path.read_bytes()))


@pytest.mark.parametrize("frontmatter", ["id: cap-test\nid: cap-test\n", "id: [bad\n", "- list\n", "id: cap-wrong\n", "id: &id cap-test\ncopy: *id\n"])
def test_malformed_yaml_visible(project, frontmatter):
    root, path = project
    path.write_text("---\n" + frontmatter + "---\nBody\n")
    report = collect(root)
    assert report["errors"] and report["counts"]["needs_review"] == 1
    raw = path.read_bytes()
    with pytest.raises((ValueError, yaml.YAMLError)):
        save(root, path, payload(root))
    assert raw == path.read_bytes()


def test_legacy_read_only_and_missing_date_not_reviewed(project):
    root, path = project
    legacy = {"review_disposition": "awaiting_evidence", "waiting_for": ["result"], "review_trigger": "arrives"}
    text = path.read_text()
    path.write_text(text.replace("status: pending_review", yaml.safe_dump(legacy).rstrip() + "\nstatus: pending_review"))
    assert item(root)["state"] == "needs_review"
    path.write_text(path.read_text().replace("status: pending_review", "reviewed_at: 2026-10-28\nstatus: pending_review"))
    raw = path.read_bytes()
    assert item(root)["state"] == "awaiting_evidence"
    assert path.read_bytes() == raw


def test_legacy_unversioned_closure_not_certified(project):
    root, path = project
    data = {"reviewed_at": "2026-10-28", "review_disposition": "absorbed", "review_reason": "checked",
            "review_refs": [{"path": "WORK.md", "quote": "User: experiment checked."}]}
    path.write_text(path.read_text().replace("status: pending_review", yaml.safe_dump(data).rstrip() + "\nstatus: pending_review"))
    assert item(root)["state"] == "needs_review"
    assert collect(root)["errors"]


def test_limits_counts_and_datetime_now(project):
    root, path = project
    for n in range(15):
        (path.parent / f"cap-{n}.md").write_text(path.read_text().replace("cap-test", f"cap-{n}"))
    report = collect(root, now=datetime(2026, 10, 29, tzinfo=timezone.utc))
    assert len(report["items"]) == 12 and report["total"] == 16 and report["omitted"] == 4
    assert report["counts"]["unreviewed"] == 16
    assert len(collect(root, limit=1000)["items"]) == 16
    assert collect(root, limit=0)["omitted"] == 16
    with pytest.raises(ValueError):
        collect(root, limit=1001)


def test_bad_quote_hash_default_scope_and_extension_preserved(project):
    root, path = project
    data = payload(root, "absorbed")
    data["refs"][0].pop("scope")
    save(root, path, data)
    assert item(root)["followup"]["refs"][0]["scope"] == "file"
    meta = yaml.safe_load(path.read_text().split("---\n")[1])
    meta["followup"]["extension"] = {"retain": True}
    path.write_text("---\n" + yaml.safe_dump(meta) + "---\nBody retained\n")
    save(root, path, payload(root, "needs_review"))
    assert item(root)["followup"]["extension"] == {"retain": True}
    bad = deepcopy(data)
    bad["refs"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash drift"):
        save(root, path, bad)


@pytest.mark.parametrize("disposition", ["absorbed", "expired", "rejected", "needs_review"])
def test_full_effective_states(project, disposition):
    root, path = project
    save(root, path, payload(root, disposition))
    current = item(root)
    assert current["state"] == disposition
    assert current["needs_review"] is (disposition == "needs_review")
    assert current["sha256"] == digest(path.read_bytes())


def test_legacy_confirmed_preserves_stored_status_even_without_review_date(project):
    root, path = project
    path.write_text(path.read_text().replace("pending_review", "confirmed"))
    assert item(root)["state"] == "confirmed"
    path.write_text(path.read_text().replace("status: confirmed", "status: confirmed\nreviewed_at: 2026-10-28"))
    assert item(root)["state"] == "confirmed"


@pytest.mark.parametrize("legacy", [
    {}, {"reviewed_at": "2026-10-28"},
    {"reviewed_at": "2026-10-28", "review_disposition": "rejected", "review_refs": ["missing.md"]},
    {"reviewed_at": None, "review_disposition": "awaiting_evidence", "review_after": "2020-01-01"},
])
def test_stored_legacy_rejection_never_blanket_reopens(project, legacy):
    root, path = project
    text = path.read_text().replace("pending_review", "rejected")
    path.write_text(text.replace("status: rejected", yaml.safe_dump(legacy).rstrip() + "\nstatus: rejected") if legacy else text)
    raw = path.read_bytes()
    current = item(root)
    assert current["state"] == "legacy_closed" and current["legacy"]
    assert not current["needs_review"] and not current["due"] and not current["drifted"]
    assert current["followup"] == {}  # Do not invent a modern closure reason/receipt.
    assert current["sha256"] == digest(raw)
    assert not collect(root)["errors"] and render_notice(root) == ""
    path.write_text(path.read_text() + "Later body edit\n")
    assert item(root)["state"] == "legacy_closed"
    assert path.read_bytes().startswith(raw)


@pytest.mark.parametrize("stored_status", ["confirmed", "rejected"])
def test_new_version_bound_followup_still_takes_precedence_and_reopens_on_drift(project, stored_status):
    root, path = project
    path.write_text(path.read_text().replace("pending_review", stored_status))
    save(root, path, payload(root, "absorbed"))
    assert item(root)["state"] == "absorbed"
    path.write_text(path.read_text() + "New candidate body\n")
    current = item(root)
    assert current["state"] == "needs_review" and current["drifted"]
    assert current["claim"] == ""


def test_changed_candidate_can_only_be_explicitly_rereviewed(project):
    root, path = project
    save(root, path, payload(root, "absorbed"))
    path.write_text(path.read_text().replace("Try experiment", "Try revised experiment"))
    assert item(root)["drifted"]
    save(root, path, payload(root, "awaiting_evidence"))
    assert item(root)["state"] == "awaiting_evidence"
    assert not item(root)["drifted"]


def test_existing_project_lock_is_used(project, monkeypatch):
    from flg.core import capture_followup as core
    from flg.core.operations import project_operation_lock
    root, path = project
    raw = path.read_bytes()
    def short_lock(project_root):
        return project_operation_lock(project_root, timeout_seconds=0)
    monkeypatch.setattr(core, "project_operation_lock", short_lock)
    with project_operation_lock(root):
        with pytest.raises(RuntimeError, match="Another FlowGrid"):
            save(root, path, payload(root))
    assert path.read_bytes() == raw


def test_capture_changed_during_reference_check_not_overwritten(project, monkeypatch):
    from flg.core import capture_followup as core
    root, path = project
    original_check = core._check_refs
    def check_and_edit(project_root, refs):
        original_check(project_root, refs)
        path.write_text(path.read_text() + "Concurrent external change\n")
    monkeypatch.setattr(core, "_check_refs", check_and_edit)
    with pytest.raises(ValueError, match="changed during review"):
        save(root, path, payload(root))
    assert "Concurrent external change" in path.read_text()
    assert "followup:" not in path.read_text()


def test_exact_retry_does_not_recheck_or_reapprove_drifted_evidence(project):
    root, path = project
    data = payload(root, "absorbed")
    expected = digest(path.read_bytes())
    record(root, "cap-test", data, expected)
    raw = path.read_bytes()
    (root / "WORK.md").write_text("Changed evidence\n")
    assert record(root, "cap-test", data, expected)["idempotent"]
    assert path.read_bytes() == raw
    assert item(root)["state"] == "needs_review"


def test_missing_ref_visible_and_unknown_payload_never_writes(project):
    root, path = project
    save(root, path, payload(root, "expired"))
    (root / "WORK.md").unlink()
    current = item(root)
    assert current["needs_review"] and current["drifted"] and current["errors"]
    raw = path.read_bytes()
    with pytest.raises(ValueError, match="Unknown review payload"):
        save(root, path, {"disposition": "rejected", "status": "confirmed"})
    assert path.read_bytes() == raw


def test_legacy_waiting_path_refs_are_unversioned_not_errors(project):
    root, path = project
    legacy = {"reviewed_at": "2026-10-28", "review_disposition": "awaiting_evidence",
              "waiting_for": ["result"], "review_trigger": "result arrives", "review_refs": ["WORK.md", "not-yet-created.md"]}
    path.write_text(path.read_text().replace("status: pending_review", yaml.safe_dump(legacy).rstrip() + "\nstatus: pending_review"))
    raw = path.read_bytes()
    current = item(root)
    assert current["state"] == "awaiting_evidence"
    assert current["unversioned_refs"] and not current["needs_review"]
    assert not collect(root)["errors"]
    assert current["followup"]["refs"] == legacy["review_refs"]
    assert path.read_bytes() == raw


def test_exact_id_selection_precedes_thousand_item_cap(project):
    root, path = project
    for n in range(1001):
        ident = f"cap-{n:04}"
        (path.parent / f"{ident}.md").write_text(path.read_text().replace("cap-test", ident))
    report = collect(root, limit=1, capture_id="cap-test")
    assert len(report["items"]) == 1 and report["items"][0]["capture_id"] == "cap-test"
    assert report["counts"]["unreviewed"] == report["total"] == 1002
    assert report["omitted"] == 0 and report["matching_total"] == 1
    assert collect(root, capture_id="cap-absent")["items"] == []


def test_synthetic_legacy_waiting_replay_keeps_statuses(project):
    root, path = project
    base = path.read_text()
    for n in range(9):
        ident = "cap-test" if n == 0 else f"cap-replay-{n}"
        text = base.replace("cap-test", ident)
        if n < 5:
            legacy = {"reviewed_at": "2026-10-28", "review_disposition": "awaiting_evidence",
                      "waiting_for": ["evidence"], "review_trigger": "evidence arrives", "review_refs": ["WORK.md"]}
            text = text.replace("status: pending_review", yaml.safe_dump(legacy).rstrip() + "\nstatus: pending_review")
        (path.parent / f"{ident}.md").write_text(text)
    before = collect(root)
    assert before["counts"]["waiting"] == 5 and before["counts"]["unreviewed"] == 4
    for n in range(5, 9):
        ident = f"cap-replay-{n}"
        capture = path.parent / f"{ident}.md"
        record(root, ident, payload(root, "awaiting_evidence" if n < 7 else "needs_review"), digest(capture.read_bytes()))
    after = collect(root)
    assert after["counts"]["waiting"] == 7 and after["counts"]["needs_review"] == 2
    assert not after["errors"]
    for capture in path.parent.glob("*.md"):
        assert yaml.safe_load(capture.read_text().split("---\n")[1])["status"] == "pending_review"


def test_real_shaped_mixed_legacy_inventory_not_blanket_reopened(project):
    root, path = project
    for n in range(29):
        ident = "cap-test" if n == 0 else f"cap-inventory-{n:02}"
        meta = {"id": ident, "claim": "Synthetic legacy candidate", "status": "pending_review"}
        if n < 7:
            meta["status"] = "confirmed"
            if n % 2:
                meta.update(reviewed_at="2026-10-28", review_refs=["missing-historical-source.md"])
        elif n < 20:
            meta["status"] = "rejected"
            if n % 2:
                meta["reviewed_at"] = "2026-10-28"
            if n % 3:
                meta.update(review_disposition="rejected", review_refs=["missing-historical-source.md"])
        elif n < 25:
            meta.update(reviewed_at="2026-10-28", review_disposition="awaiting_evidence",
                        waiting_for=["Experiment results"], review_trigger="Results arrive",
                        review_refs=["WORK.md"])
        (path.parent / f"{ident}.md").write_text("---\n" + yaml.safe_dump(meta) + "---\nHistorical candidate body\n")
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()}
    report = collect(root, limit=1000)
    assert report["total"] == 29 and report["omitted"] == 0
    assert report["counts"] == {
        "confirmed": 7, "legacy_closed": 13, "awaiting_evidence": 5, "waiting": 5,
        "unreviewed": 4, "needs_review": 0, "absorbed": 0, "expired": 0, "rejected": 0,
    }
    assert not report["errors"]
    assert sum(current["needs_review"] for current in report["items"]) == 4
    assert all(not current["followup"] for current in report["items"] if current["state"] == "legacy_closed")
    assert "4 need explicit review" in render_notice(root)
    filtered = collect(root, limit=1, capture_id="cap-inventory-19")
    assert filtered["items"][0]["state"] == "legacy_closed"
    assert filtered["counts"] == report["counts"]
    after = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()}
    assert before == after


def test_review_and_state_filters_precede_limit_after_thousand_confirmed(project):
    root, path = project
    original = path.read_text()
    for n in range(1000):
        for prefix, status in (("a-confirmed", "confirmed"), ("z-unreviewed", "pending_review")):
            ident = f"cap-{prefix}-{n:04}"
            (path.parent / f"{ident}.md").write_text(
                original.replace("cap-test", ident).replace("status: pending_review", f"status: {status}"))
    by_state = collect(root, state="unreviewed", limit=12)
    by_review = collect(root, needs_review_only=True, limit=12)
    assert by_state == by_review
    assert len(by_state["items"]) == 12
    assert all(current["state"] == "unreviewed" for current in by_state["items"])
    assert by_state["total"] == 2001 and by_state["matching_total"] == 1001
    assert by_state["omitted"] == 989
    assert by_state["counts"]["confirmed"] == 1000 and by_state["counts"]["unreviewed"] == 1001
    exact = collect(root, capture_id="cap-z-unreviewed-0999", state="unreviewed", needs_review_only=True, limit=1)
    assert exact["matching_total"] == 1 and exact["omitted"] == 0
    assert exact["items"][0]["capture_id"] == "cap-z-unreviewed-0999"
    mismatch = collect(root, capture_id="cap-z-unreviewed-0999", state="confirmed", limit=1)
    assert mismatch["items"] == [] and mismatch["matching_total"] == mismatch["omitted"] == 0
    assert mismatch["counts"] == by_state["counts"]


@pytest.mark.parametrize("stored_status,effective", [("confirmed", "confirmed"), ("rejected", "legacy_closed")])
def test_early_legacy_branches_apply_all_filters(project, stored_status, effective):
    root, path = project
    path.write_text(path.read_text().replace("pending_review", stored_status))
    selected = collect(root, capture_id="cap-test", state=effective, limit=1)
    assert selected["matching_total"] == 1 and selected["items"][0]["state"] == effective
    assert collect(root, needs_review_only=True)["items"] == []
    assert collect(root, state="unreviewed")["matching_total"] == 0
    assert collect(root, capture_id="cap-missing", state=effective)["matching_total"] == 0
    zero_limit = collect(root, state=effective, limit=0)
    assert zero_limit["matching_total"] == zero_limit["omitted"] == 1
    assert zero_limit["counts"][effective] == 1


@pytest.mark.parametrize("failure", ["oversized", "bad_utf8", "permission", "missing_quote", "invalid_schema", "null_followup"])
def test_any_followup_validation_failure_blanks_claim_and_marks_drift(project, monkeypatch, failure):
    from flg.core import capture_followup as core
    root, path = project
    save(root, path, payload(root, "absorbed", "quote"))
    if failure == "oversized":
        (root / "WORK.md").write_text("User: experiment checked.\n" + "x" * (2 * 1024 * 1024))
    elif failure == "bad_utf8":
        (root / "WORK.md").write_bytes(b"User: experiment checked.\n\xff")
    elif failure == "permission":
        original_read = core._read
        def denied(project_root, relative):
            if relative == "WORK.md":
                raise PermissionError("Access denied for synthetic evidence")
            return original_read(project_root, relative)
        monkeypatch.setattr(core, "_read", denied)
    elif failure == "missing_quote":
        (root / "WORK.md").write_text("Evidence no longer present\n")
    else:
        meta = yaml.safe_load(path.read_text().split("---\n")[1])
        if failure == "null_followup":
            meta["followup"] = None
        else:
            meta["followup"]["schema_version"] = 999
        path.write_text("---\n" + yaml.safe_dump(meta) + "---\nOriginal body\n")
    raw = path.read_bytes()
    report = collect(root, state="needs_review", needs_review_only=True)
    current = report["items"][0]
    assert current["state"] == "needs_review" and current["needs_review"] and current["drifted"]
    assert current["claim"] == "" and current["errors"] and report["errors"]
    assert current["sha256"] == digest(raw)
    assert path.read_bytes() == raw


@pytest.mark.parametrize("kwargs", [{"state": "waiting"}, {"state": []}, {"needs_review_only": "yes"}])
def test_invalid_collector_filters_visible(project, kwargs):
    root, _ = project
    with pytest.raises(ValueError):
        collect(root, **kwargs)
