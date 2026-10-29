"""Public synthetic end-to-end candidate lifecycle checks."""
import json
from pathlib import Path
import subprocess
import sys

from typer.testing import CliRunner
import yaml
import pytest

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


@pytest.mark.parametrize('choice,status', [('a', 'confirmed'), ('r', 'rejected')])
@pytest.mark.parametrize('disposition', ['awaiting_evidence', 'needs_review'])
@pytest.mark.parametrize('newline', [b'\n', b'\r\n'])
def test_formal_review_closes_followup_without_drift(tmp_path, monkeypatch, choice, status, disposition, newline):
    path, data = seed(tmp_path, monkeypatch)
    assert runner.invoke(app, ['reindex']).exit_code == 0
    path.write_bytes(path.read_bytes().replace(b'\n', newline))
    (tmp_path / 'check.md').write_text('Synthetic pilot evidence.')
    data['refs'] = [{'path': 'check.md', 'quote': 'Synthetic pilot evidence.',
                     'scope': 'file', 'sha256': digest('Synthetic pilot evidence.')}]
    data['disposition'] = disposition
    data['review_after'] = '2001-01-01'
    record(tmp_path, path.stem, data, digest(path.read_bytes()))
    from flg.core.capture_followup import _parse
    body = _parse(path.read_bytes(), path.stem)[1]
    before = yaml.safe_load(path.read_text().split('---', 2)[1])
    result = runner.invoke(app, ['capture', 'review'], input=choice + '\n')
    assert result.exit_code == 0, result.output
    current = collect(tmp_path)['items'][0]
    assert current['state'] == status
    assert not current['needs_review'] and not current['drifted']
    assert not collect(tmp_path)['errors']
    assert json.loads(runner.invoke(app, ['capture', 'followups']).output)['items'] == []
    meta = yaml.safe_load(path.read_text().split('---', 2)[1])
    assert meta['status'] == status
    assert meta['followup_history'][:len(before['followup_history'])] == before['followup_history']
    assert meta['followup_history'][-1]['previous_followup'] == before['followup']
    assert _parse(path.read_bytes(), path.stem)[1] == body
    doctor = runner.invoke(app, ['doctor', '--strict'])
    assert doctor.exit_code == 0, doctor.output
    (tmp_path / 'check.md').write_text('Changed pilot evidence.')
    assert collect(tmp_path)['items'][0]['drifted']
    (tmp_path / 'check.md').write_text('Synthetic pilot evidence.')
    # A new explicit follow-up must replace, rather than inherit, the formal
    # outcome marker; candidate status alone must never approve that review.
    record(tmp_path, path.stem, data, digest(path.read_bytes()))
    assert collect(tmp_path)['items'][0]['state'] == 'needs_review'
    assert 'formal_outcome' not in collect(tmp_path)['items'][0]['followup']
    path.write_text(path.read_text() + '\nChanged candidate body.\n')
    assert collect(tmp_path)['items'][0]['drifted']


@pytest.mark.parametrize('followup', [None, {}, False, [], ''])
def test_invalid_falsy_followup_cannot_auto_confirm(tmp_path, monkeypatch, followup):
    path, _ = seed(tmp_path, monkeypatch)
    front, body = path.read_text().split('---', 2)[1:]
    meta = yaml.safe_load(front)
    meta['followup'] = followup
    path.write_text('---\n' + yaml.safe_dump(meta) + '---' + body)
    raw = path.read_bytes()
    formal = (tmp_path / 'DECISIONS.md').read_bytes()
    assert collect(tmp_path)['errors']
    result = runner.invoke(app, ['capture', 'review', '--auto-confirm'])
    assert result.exit_code == 0, result.output
    assert path.read_bytes() == raw
    assert (tmp_path / 'DECISIONS.md').read_bytes() == formal


def test_invalid_review_cannot_be_silently_rebased_by_interactive_accept(tmp_path, monkeypatch):
    path, data = seed(tmp_path, monkeypatch)
    record(tmp_path, path.stem, data, digest(path.read_bytes()))
    path.write_text(path.read_text() + '\nUnreviewed new claim.\n')
    before = path.read_bytes()
    formal = (tmp_path / 'DECISIONS.md').read_bytes()
    result = runner.invoke(app, ['capture', 'review'], input='a\n')
    assert result.exit_code == 0, result.output
    assert path.read_bytes() == before
    assert (tmp_path / 'DECISIONS.md').read_bytes() == formal


def test_capture_changed_during_formal_prompt_is_not_overwritten(tmp_path, monkeypatch):
    from flg.commands import capture
    path, data = seed(tmp_path, monkeypatch)
    record(tmp_path, path.stem, data, digest(path.read_bytes()))
    original = path.read_bytes()
    formal = (tmp_path / 'DECISIONS.md').read_bytes()
    def prompt(*args, **kwargs):
        path.write_bytes(original + b'Concurrent candidate change.\n')
        return 'a'
    monkeypatch.setattr(capture.typer, 'prompt', prompt)
    result = runner.invoke(app, ['capture', 'review'])
    assert result.exit_code == 0
    assert 'changed during formal review' in result.output
    assert path.read_bytes() == original + b'Concurrent candidate change.\n'
    assert (tmp_path / 'DECISIONS.md').read_bytes() == formal


def test_later_conflict_does_not_lose_earlier_accepted_decision(tmp_path, monkeypatch):
    from flg.commands import capture
    path, data = seed(tmp_path, monkeypatch)
    record(tmp_path, path.stem, data, digest(path.read_bytes()))
    second = path.with_name('cap-zz-second.md')
    second.write_text(path.read_text().replace(path.stem, second.stem))
    record(tmp_path, second.stem, data, digest(second.read_bytes()))
    calls = []
    def prompt(*args, **kwargs):
        calls.append(True)
        if len(calls) == 2:
            second.write_bytes(second.read_bytes() + b'Concurrent edit.\n')
        return 'a'
    monkeypatch.setattr(capture.typer, 'prompt', prompt)
    result = runner.invoke(app, ['capture', 'review'])
    assert result.exit_code == 0, result.output
    assert len(calls) == 2
    assert '## D-001' in (tmp_path / 'DECISIONS.md').read_text()
    assert '## D-002' not in (tmp_path / 'DECISIONS.md').read_text()
    assert yaml.safe_load(second.read_text().split('---', 2)[1])['status'] == 'pending_review'
    assert collect(tmp_path, capture_id=path.stem)['items'][0]['state'] == 'confirmed'


@pytest.mark.parametrize('change_candidate', [False, True])
def test_old_writer_retained_outcome_cannot_hide_new_review(tmp_path, monkeypatch, change_candidate):
    from flg.core.capture_followup import _parse, _basis
    path, data = seed(tmp_path, monkeypatch)
    record(tmp_path, path.stem, data, digest(path.read_bytes()))
    assert runner.invoke(app, ['capture', 'review'], input='a\n').exit_code == 0
    meta, body = _parse(path.read_bytes(), path.stem)
    # Model the old writer: it preserves unknown formal_outcome, replaces
    # defined review fields, and recalculates only the outer candidate basis.
    if change_candidate:
        body += 'Changed candidate.\n'
    meta['followup'].update(data)
    meta['followup']['disposition'] = 'needs_review'
    meta['followup']['basis_sha256'] = _basis(meta, body)
    path.write_text('---\n' + yaml.safe_dump(meta) + '---\n' + body)
    current = collect(tmp_path)['items'][0]
    assert current['state'] == 'needs_review' and current['drifted']
