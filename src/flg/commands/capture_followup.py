"""Explicit candidate follow-up; no approval or bulk cleanup."""
import json
from pathlib import Path
from typing import Optional

import typer

from ..core import capture_followup as followup
from ..core.source_receipts import parse_json, read_bytes


def _run(action):
    try:
        result = action()
    except (ValueError, OSError, RuntimeError, TypeError, KeyError) as exc:
        typer.echo(json.dumps({'error': str(exc)}, ensure_ascii=False))
        raise typer.Exit(2)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return result


def capture_followups(
    capture_id: Optional[str] = typer.Option(None, '--capture'),
    state: Optional[str] = typer.Option(None, '--state'),
    all_states: bool = typer.Option(False, '--all', help='Include waiting and closed records'),
    limit: int = typer.Option(12, '--limit', min=1, max=100),
):
    """Read current review queue; age alone never approves or closes a candidate."""
    def action():
        result = followup.collect(Path.cwd(), limit=limit, capture_id=capture_id, state=state,
                                  needs_review_only=not (capture_id or state or all_states))
        selected = result['items']
        if capture_id and not selected:
            raise ValueError('Unknown candidate; inspect errors and capture list')
        total = result['matching_total']
        result['scan_total'] = result['total']
        result.update(items=selected[:limit], total=total, omitted=max(0, total-len(selected[:limit])),
                      expand='flg capture followups --capture CAPTURE_ID', formal_state_changed=False)
        return result
    view = _run(action)
    if view['errors']:
        raise typer.Exit(1)


def capture_followup_record(
    capture_id: str,
    input: str = typer.Option(..., '--input', help='Project-relative JSON review record'),
    expected_sha256: str = typer.Option(..., '--expected-sha256', help='Capture version actually reviewed'),
):
    """Record reviewed disposition in one capture with compare-and-swap protection."""
    _run(lambda: followup.record(Path.cwd(), capture_id,
                                parse_json(read_bytes(Path.cwd(), input)), expected_sha256))
