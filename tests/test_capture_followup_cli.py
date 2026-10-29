"""Public synthetic end-to-end candidate lifecycle checks."""
import json
from pathlib import Path
import subprocess
import sys

from typer.testing import CliRunner
import yaml

from flg.cli import app
from flg.core.capture_followup import collect, record
from flg.core.source_receipts import digest
from flg.commands.context import build_context_pack
from flg.commands.handoff import generate_handoff_summary

runner = CliRunner()


def seed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ['init', 'Synthetic follow-up']).exit_code == 0
    assert runner.invoke(app, ['capture', 'add', '--claim', 'Pilot needs results',
                              '--rationale', 'Evidence is still awaited',
                              '--confidence', 'confirmed', '--evidence', 'User: Pilot needs results',
                              '--confirmation-event-id', 'event-1']).exit_code == 0
    path = next((tmp_path / '.flg/captures').glob('cap-*.md'))
    data = {'schema_version': 1, 'disposition': 'awaiting_evidence', 'reason': 'Actual review',
            'waiting_for': ['Pilot results'], 'review_trigger': 'Results arrive',
            'reviewed_at': '2026-10-29T00:00:00Z', 'refs': []}
    return path, data


def test_cli_record_followups_and_auto_review_does_not_promote(tmp_path, monkeypatch):
    path, data = seed(tmp_path, monkeypatch)
    formal = (tmp_path / 'DECISIONS.md').read_bytes()
    (tmp_path / 'review.json').write_text(json.dumps(data))
    result = runner.invoke(app, ['capture', 'followup-record', path.stem, '--input', 'review.json',
                                '--expected-sha256', digest(path.read_bytes())])
    assert result.exit_code == 0, result.output
    raw = path.read_bytes()
    view = runner.invoke(app, ['capture', 'followups'])
    assert view.exit_code == 0 and json.loads(view.output)['items'] == []
    view = runner.invoke(app, ['capture', 'followups', '--capture', path.stem])
    assert json.loads(view.output)['items'][0]['state'] == 'awaiting_evidence'
    assert runner.invoke(app, ['capture', 'review', '--auto-confirm']).exit_code == 0
    assert path.read_bytes() == raw
    assert (tmp_path / 'DECISIONS.md').read_bytes() == formal


def test_due_notice_in_resume_manifest_work_and_handoff(tmp_path, monkeypatch):
    path, data = seed(tmp_path, monkeypatch)
    (tmp_path / 'work.md').write_text('## Current Action\n\nWait for pilot results.\n')
    state_path = tmp_path / '.flg/state.json'
    state = json.loads(state_path.read_text())
    state['work_source'] = {'schema_version': '1', 'path': 'work.md'}
    state_path.write_text(json.dumps(state))
    data['review_after'] = '2001-01-01'
    record(tmp_path, path.stem, data, digest(path.read_bytes()))
    formal = (tmp_path / 'DECISIONS.md').read_bytes()
    for mode in ['resume', 'manifest', 'work']:
        content, _ = build_context_pack(tmp_path, mode=mode, budget=4000)
        assert 'flg capture followups' in content
    assert 'flg capture followups' in generate_handoff_summary(tmp_path)
    result = subprocess.run([sys.executable, '-c', 'from flg.cli import app; app()', 'capture', 'followups'],
                            cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['items'][0]['state'] == 'needs_review'
    assert (tmp_path / 'DECISIONS.md').read_bytes() == formal


def test_no_new_followup_bypasses_closure_and_waiting_not_overdue_by_age(tmp_path, monkeypatch):
    path, data = seed(tmp_path, monkeypatch)
    data['reviewed_at'] = '2001-01-01'
    record(tmp_path, path.stem, data, digest(path.read_bytes()))
    assert collect(tmp_path)['counts']['awaiting_evidence'] == 1
    data['disposition'] = 'rejected'
    (tmp_path / 'check.md').write_text('User: Explicitly do not proceed.')
    data['refs'] = [{'path': 'check.md', 'quote': 'User: Explicitly do not proceed.',
                     'scope': 'quote', 'sha256': digest('User: Explicitly do not proceed.')}]
    record(tmp_path, path.stem, data, digest(path.read_bytes()))
    raw = path.read_bytes()
    assert runner.invoke(app, ['capture', 'review', '--auto-confirm']).exit_code == 0
    assert path.read_bytes() == raw
    assert collect(tmp_path)['counts']['rejected'] == 1


def test_legacy_wait_without_disposition_cannot_auto_promote(tmp_path, monkeypatch):
    path, _ = seed(tmp_path, monkeypatch)
    text = path.read_text()
    front, body = text.split('---', 2)[1:]
    meta = yaml.safe_load(front)
    meta.update(reviewed_at='2026-10-29', waiting_for=['Results'], review_trigger='Results arrive')
    path.write_text('---\n' + yaml.safe_dump(meta) + '---' + body)
    raw = path.read_bytes()
    formal = (tmp_path / 'DECISIONS.md').read_bytes()
    assert runner.invoke(app, ['capture', 'review', '--auto-confirm']).exit_code == 0
    assert path.read_bytes() == raw
    assert (tmp_path / 'DECISIONS.md').read_bytes() == formal


def test_list_does_not_reexpose_drifted_claim(tmp_path, monkeypatch):
    path, data = seed(tmp_path, monkeypatch)
    (tmp_path / 'check.md').write_text('Evidence v1')
    data['refs'] = [{'path': 'check.md', 'quote': 'Evidence v1', 'scope': 'file', 'sha256': digest('Evidence v1')}]
    record(tmp_path, path.stem, data, digest(path.read_bytes()))
    (tmp_path / 'check.md').write_text('Evidence changed')
    result = runner.invoke(app, ['capture', 'list'])
    assert result.exit_code == 0
    assert 'Pilot needs results' not in result.output
    assert 'suppressed' in result.output
