"""Explicit, local capture review metadata. Reads never repair or promote state.

Hashes in public results cover the complete capture bytes. The internal basis
hash excludes only followup and followup_history, binding review to candidate
content while permitting append-only review metadata updates.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re

import yaml

from .operations import atomic_write_text, project_operation_lock
from .source_receipts import checked_path, digest, read_bytes, require, valid_hash

DISPOSITIONS = {"awaiting_evidence", "needs_review", "absorbed", "expired", "rejected"}
CLOSED = {"absorbed", "expired", "rejected"}
STATES = ("unreviewed", "awaiting_evidence", "needs_review", "absorbed", "expired", "rejected", "confirmed", "legacy_closed")
MAX_BYTES = 2 * 1024 * 1024
READ_ERRORS = (ValueError, OSError, UnicodeError, TypeError, yaml.YAMLError)


class _Loader(yaml.SafeLoader):
    pass


def _mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        require(isinstance(key, str) and key not in result, "Duplicate or non-string YAML key")
        result[key] = loader.construct_object(value_node, deep=True)
    return result


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _id(value):
    require(isinstance(value, str) and re.fullmatch(r"cap-[A-Za-z0-9][A-Za-z0-9_-]{0,119}", value), "Invalid capture ID")
    return value


def _read(root, path):
    require(checked_path(root, path).stat().st_size <= MAX_BYTES, "File exceeds 2 MiB limit")
    raw = read_bytes(root, path)
    require(len(raw) <= MAX_BYTES, "File exceeds 2 MiB limit")
    return raw


def _parse(raw, ident):
    text = raw.decode("utf-8")
    match = re.match(r"\A---\r?\n(.*?)^---[ \t]*\r?\n", text, re.S | re.M)
    require(match is not None, "Missing or malformed capture YAML frontmatter")
    # Aliases and anchors are unnecessary here and can hide recursive structures.
    try:
        require(not any(isinstance(t, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken))
                        for t in yaml.scan(match[1])), "YAML aliases/anchors unsupported")
        meta = yaml.load(match[1], Loader=_Loader)
    except yaml.YAMLError as exc:
        raise ValueError("Malformed capture YAML frontmatter") from exc
    require(isinstance(meta, dict), "Capture metadata must be a mapping")
    require(meta.get("id") == ident, "Capture filename/ID mismatch")
    history = meta.get("followup_history", [])
    require(isinstance(history, list) and all(isinstance(x, dict) for x in history), "Malformed followup history")
    return meta, text[match.end():]


def _basis(meta, body):
    candidate = {k: v for k, v in meta.items() if k not in {"followup", "followup_history"}}
    return digest(json.dumps(candidate, sort_keys=True, ensure_ascii=False, default=str) + "\n" + body)


def bind_formal_review(meta, body):
    """Bind an explicit formal outcome without losing the prior follow-up.

    Called only by interactive capture review, after its validation gate. This
    does not grant authority to followup-record or repair an invalid review.
    """
    require(meta.get('status') in {'confirmed', 'rejected'}, 'Expected formal review status')
    previous = deepcopy(meta['followup'])
    _validate(previous)
    outcome = {'status': meta['status'], 'reviewed_at': meta['reviewed_at']}
    meta['followup'] = {**deepcopy(previous), 'formal_outcome': outcome,
                        'basis_sha256': _basis(meta, body)}
    outcome['followup_sha256'] = _followup_basis(meta['followup'])
    meta.setdefault('followup_history', []).append({
        'previous_followup': previous, 'formal_outcome': deepcopy(outcome),
        'followup': deepcopy(meta['followup'])})


def _followup_basis(data):
    return digest(json.dumps({k: v for k, v in data.items() if k != 'formal_outcome'},
                             sort_keys=True, ensure_ascii=False, default=str))


def _time(value):
    require(isinstance(value, (str, date, datetime)) and bool(str(value).strip()), "Expected ISO date/time")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Expected ISO date/time") from exc
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _validate(data, require_date=True):
    require(isinstance(data, dict), "followup must be an object")
    require(type(data.get("schema_version")) is int and data["schema_version"] == 1, "Unsupported followup schema_version")
    require(isinstance(data.get("disposition"), str) and data["disposition"] in DISPOSITIONS, "Invalid followup disposition")
    require(isinstance(data.get("reason", ""), str), "reason must be text")
    waiting = data.get("waiting_for", [])
    require(isinstance(waiting, list) and len(waiting) <= 50 and all(_text(x) for x in waiting), "waiting_for must be a list of nonempty strings")
    require(isinstance(data.get("review_trigger", ""), str), "review_trigger must be text")
    if data["disposition"] == "awaiting_evidence":
        require(waiting and _text(data.get("review_trigger")), "Awaiting evidence requires waiting_for and review_trigger")
    refs = data.get("refs", [])
    require(isinstance(refs, list) and len(refs) <= 50, "refs must be a list (max 50)")
    if data["disposition"] in CLOSED:
        require(_text(data.get("reason")) and refs, "Closure requires explicit reason and checked refs")
    if require_date or data.get("reviewed_at"):
        _time(data.get("reviewed_at"))
    if data.get("review_after") is not None:
        _time(data["review_after"])
    for ref in refs:
        require(isinstance(ref, dict) and _text(ref.get("path")) and _text(ref.get("quote")), "Each ref requires path and exact quote")
        require(ref.get("scope", "file") in ("file", "quote"), "Invalid ref scope")
        require(valid_hash(ref.get("sha256")), "Unversioned ref: SHA-256 required")


def _check_refs(root, refs):
    for ref in refs:
        raw = _read(root, ref["path"])
        quote = ref["quote"]
        text = raw.decode("utf-8")
        require(quote in text, "Reference quote missing or changed")
        if ref.get("scope", "file") == "quote":
            start = text.find(quote)
            require(text.find(quote, start + 1) < 0, "Quote reference must occur uniquely")
            current = digest(quote)
        else:
            current = digest(raw)
        require(current == ref["sha256"], "Reference hash drift: reread evidence")


def _legacy(meta):
    disposition = meta.get("review_disposition")
    if not disposition:
        disposition = "awaiting_evidence" if meta.get("waiting_for") else "needs_review"
    return {"schema_version": 1, "disposition": disposition,
            "reason": meta.get("review_reason", ""), "waiting_for": meta.get("waiting_for", []),
            "review_trigger": meta.get("review_trigger", ""), "review_after": meta.get("review_after"),
            "reviewed_at": meta.get("reviewed_at"), "refs": meta.get("review_refs", [])}


def collect(root, now=None, limit=12, capture_id=None, state=None, needs_review_only=False) -> dict:
    """Return bounded all-state items; filter ``needs_review`` for action lists.

    Counts cover all scanned captures, not just returned items. Errors are capped
    at 50, with total_errors retaining the full number. Naive dates use UTC;
    date-only review_after becomes due at midnight on that date (inclusive).
    Stored confirmed/rejected statuses without new followup retain their legacy
    meaning, regardless of absent review dates or unversioned legacy references.
    legacy_closed records preserve rejection without inventing a closure reason.
    ID, effective state, and review-only filters compose before the display cap;
    total/counts/errors remain global, matching_total/omitted describe matches.
    """
    root = Path(root)
    if capture_id is not None:
        _id(capture_id)
    require(state is None or (isinstance(state, str) and state in STATES), "Invalid followup state filter")
    require(type(needs_review_only) is bool, "needs_review_only must be a boolean")
    require(type(limit) is int and 0 <= limit <= 1000, "limit must be between 0 and 1000")
    instant = _time(now) if now is not None else datetime.now(timezone.utc)
    counts = dict.fromkeys(STATES, 0)
    counts["waiting"] = 0
    items, errors = [], []
    total = total_errors = matching_total = 0

    def error(ident, message):
        nonlocal total_errors
        total_errors += 1
        if len(errors) < 50:
            errors.append({"capture_id": ident, "error": str(message)[:300]})

    def include(item):
        nonlocal matching_total
        item["needs_review"] = item["state"] in {"unreviewed", "needs_review"}
        counts[item["state"]] += 1
        if item["state"] == "awaiting_evidence":
            counts["waiting"] += 1
        if ((capture_id is None or item["capture_id"] == capture_id)
                and (state is None or item["state"] == state)
                and (not needs_review_only or item["needs_review"])):
            matching_total += 1
            if len(items) < limit:
                items.append(item)

    try:
        folder = checked_path(root, ".flg/captures")
        paths = sorted(folder.glob("*.md")) if folder.exists() else []
    except READ_ERRORS as exc:
        error(None, exc)
        paths = []
    for path in paths:
        ident = path.stem
        total += 1
        item = {"capture_id": ident, "path": f".flg/captures/{path.name}", "state": "unreviewed",
                "needs_review": True, "sha256": None, "claim": "", "followup": {},
                "due": False, "drifted": False, "legacy": False, "unversioned_refs": False, "errors": []}
        try:
            _id(ident)
            raw = _read(root, item["path"])
            item["sha256"] = digest(raw)
            meta, body = _parse(raw, ident)
            item["claim"] = str(meta.get("claim", ""))[:500]
            if "followup" not in meta and meta.get("status") in ("confirmed", "rejected"):
                # Historical formal outcomes are already stored facts, not new
                # followup declarations to validate against today's schema.
                # Preserve their coarse meaning without manufacturing refs,
                # review dates, reasons, or a version-bound closure receipt.
                item["state"] = "confirmed" if meta["status"] == "confirmed" else "legacy_closed"
                item["legacy"] = True
                item["needs_review"] = False
                item["unversioned_refs"] = bool(meta.get("review_refs"))
                include(item)
                continue
            has_legacy = any(k in meta for k in ("reviewed_at", "review_disposition", "waiting_for", "review_trigger", "review_refs"))
            data = meta.get("followup") if "followup" in meta else (_legacy(meta) if has_legacy else None)
            item["legacy"] = "followup" not in meta and has_legacy
            if data is not None or "followup" in meta:
                require(isinstance(data, dict), "followup must be an object")
                # Bound output even for oversized hand-edited review metadata.
                require(len(json.dumps(data, default=str)) <= 32000, "Followup metadata exceeds output limit")
                item["followup"] = deepcopy(data)
                legacy_waiting = item["legacy"] and data.get("disposition") == "awaiting_evidence"
                refs = data.get("refs", [])
                checked_refs = refs
                if legacy_waiting:
                    require(isinstance(refs, list) and len(refs) <= 50, "refs must be a list (max 50)")
                    # Historical waiting records used paths alone. They describe
                    # a wait, not checked evidence or permission to close it.
                    require(all(_text(ref) or isinstance(ref, dict) for ref in refs), "Malformed legacy review_refs")
                    checked_refs = [ref for ref in refs if isinstance(ref, dict) and valid_hash(ref.get("sha256"))]
                    item["unversioned_refs"] = len(checked_refs) != len(refs)
                _validate({**data, "refs": checked_refs})
                if not item["legacy"]:
                    require(valid_hash(data.get("basis_sha256")), "Missing version-bound capture basis")
                    require(data["basis_sha256"] == _basis(meta, body), "Capture basis drift: explicit rereview required")
                elif data["disposition"] in CLOSED:
                    # Legacy hashes still check refs, but cannot certify candidate version.
                    _check_refs(root, data.get("refs", []))
                    raise ValueError("Legacy closure is unversioned; explicit rereview required")
                _check_refs(root, checked_refs)
                item["state"] = data["disposition"]
                outcome = data.get('formal_outcome')
                if outcome is not None:
                    require(not item['legacy'] and isinstance(outcome, dict)
                            and outcome.get('status') in {'confirmed', 'rejected'}
                            and outcome['status'] == meta.get('status')
                            and outcome.get('reviewed_at') == meta.get('reviewed_at')
                            and outcome.get('followup_sha256') == _followup_basis(data),
                            'Invalid formal review outcome')
                    _time(outcome.get('reviewed_at'))
                    item['state'] = outcome['status']
                item["due"] = outcome is None and data.get("review_after") is not None and instant >= _time(data["review_after"])
                if item["due"]:
                    item["state"] = "needs_review"
        except READ_ERRORS as exc:
            message = str(exc)[:300]
            item["state"] = "needs_review"
            item["errors"].append(message)
            # Any unreadable/invalid review basis invalidates the current action
            # view, regardless of exception wording (size, encoding, access,
            # schema, missing quote, hash mismatch, or malformed capture).
            item["drifted"] = True
            item["claim"] = ""
            error(ident, message)
        include(item)
    return {"items": items, "counts": counts, "errors": errors, "total": total,
            "omitted": matching_total - len(items), "matching_total": matching_total,
            "total_errors": total_errors}


def record(root, capture_id, payload, expected_sha256) -> dict:
    """Write only the selected capture; exact last-operation retry precedes CAS.

    Invalid input/CAS raises ValueError, filesystem/lock errors remain visible.
    reviewed_at may be supplied explicitly or is filled at successful record time.
    """
    root = Path(root)
    ident = _id(capture_id)
    require(isinstance(payload, dict), "Review payload must be an object")
    require(valid_hash(expected_sha256), "expected_sha256 must be a SHA-256")
    require(set(payload) <= {"schema_version", "disposition", "reason", "waiting_for", "review_trigger", "review_after", "refs", "reviewed_at"}, "Unknown review payload field")
    request = deepcopy(payload)
    # Validate paths before acquiring a lock (which itself lives below .flg).
    path = checked_path(root, f".flg/captures/{ident}.md")
    checked_path(root, ".flg/.operation.lock")
    with project_operation_lock(root):
        raw = _read(root, f".flg/captures/{ident}.md")
        meta, body = _parse(raw, ident)
        history = meta.get("followup_history", [])
        previous = history[-1] if history else {}
        retry = (previous.get("expected_sha256") == expected_sha256 and previous.get("payload") == request
                 and previous.get("followup") == meta.get("followup")
                 and meta.get("followup", {}).get("basis_sha256") == _basis(meta, body))
        if retry:
            return {"applied": False, "idempotent": True, "capture_id": ident,
                    "path": str(path.relative_to(root.resolve())), "sha256": digest(raw), "followup": meta["followup"]}
        require(digest(raw) == expected_sha256, "Capture CAS conflict: reread capture before reviewing")
        data = deepcopy(payload)
        data.setdefault("schema_version", 1)
        data.setdefault("reviewed_at", datetime.now(timezone.utc).isoformat())
        data.setdefault("reason", "")
        data.setdefault("waiting_for", [])
        data.setdefault("review_trigger", "")
        data.setdefault("refs", [])
        for ref in data["refs"] if isinstance(data["refs"], list) else []:
            if isinstance(ref, dict):
                ref.setdefault("scope", "file")
        require(len(json.dumps(data, default=str)) <= 32000, "Followup metadata exceeds output limit")
        _validate(data)
        _check_refs(root, data["refs"])
        data["basis_sha256"] = _basis(meta, body)
        old = meta.get("followup", {})
        require(isinstance(old, dict), "Malformed existing followup")
        # Preserve extension fields while replacing the defined review fields.
        data = {**{k: v for k, v in old.items() if k not in {
            "schema_version", "disposition", "reason", "waiting_for", "review_trigger",
            "review_after", "refs", "reviewed_at", "basis_sha256", "formal_outcome"}}, **data}
        if not history and old:
            history = [{"followup": deepcopy(old)}]
        history.append({"expected_sha256": expected_sha256, "payload": request, "followup": deepcopy(data)})
        meta["followup"] = data
        meta["followup_history"] = history
        updated = "---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + "---\n" + body
        require(len(updated.encode("utf-8")) <= MAX_BYTES, "Capture history exceeds 2 MiB limit")
        _check_refs(root, data["refs"])
        require(digest(_read(root, f".flg/captures/{ident}.md")) == expected_sha256, "Capture changed during review")
        atomic_write_text(checked_path(root, f".flg/captures/{ident}.md"), updated)
        return {"applied": True, "idempotent": False, "capture_id": ident,
                "path": f".flg/captures/{ident}.md", "sha256": digest(updated), "followup": data}


def render_notice(root) -> str:
    """Bounded aggregate only: ordinary waiting does not repeat reminders."""
    report = collect(root, limit=0)
    pending = report["counts"]["unreviewed"] + report["counts"]["needs_review"]
    if not pending and not report["total_errors"]:
        return ""
    return (f"Capture follow-up: {pending} need explicit review; "
            f"{report['counts']['waiting']} awaiting evidence; {report['total_errors']} errors. "
            "No formal status or decision changes were made.\n"
            "Expand: `flg capture followups`; inspect the candidate and evidence before acting.\n\n")
