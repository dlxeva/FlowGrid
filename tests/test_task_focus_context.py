"""Synthetic task-focus integration; all fixtures are disposable local projects."""
from datetime import datetime

import pytest
from typer.testing import CliRunner

from flg.cli import app
from flg.commands import context as ctx


def decision(ident, title, statement, status='confirmed', reversal='Review after new evidence.'):
    return (f'## {ident} | {title}\n\n### Final Decision\n{statement}\n\n'
            f'### Decision Rationale\nBounded project choice.\n\n### Rejected Alternatives\n'
            f'Unreviewed expansion.\n\n### Reversal Conditions\n{reversal}\n\n### Status\n{status}\n\n')


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert CliRunner().invoke(app, ['init', 'Synthetic history']).exit_code == 0
    (tmp_path / 'SNAPSHOT.md').write_text('# Snapshot\n\n## Current Core Goal\nPrepare the local brief.\n\n'
        '## Next Highest Priority Action\nReview the local draft.\n\n'
        '## Hard Constraints\n- Never publish without approval.\n', encoding='utf-8')
    ledger = decision('D-001', 'Brand narrative and user agency', 'User agency guides the brand narrative.',
                      reversal='Review if audience research changes.')
    ledger += decision('D-002', 'Cloud migration', 'Use cloud migration.', 'superseded')
    ledger += decision('D-003', 'Funding budget', 'Defer the laboratory plan under the budget limit.',
                       reversal='Review if funding changes.')
    for number in range(4, 12):
        ledger += decision(f'D-{number:03}', f'Local formatting {number}', f'Use layout option {number}.')
    (tmp_path / 'DECISIONS.md').write_text(ledger, encoding='utf-8')
    yield tmp_path


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_default_path_unchanged_and_query_preserves_current_work(project, monkeypatch):
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 17, tzinfo=tz)
    monkeypatch.setattr(ctx, 'datetime', Frozen)
    baseline, baseline_meta = ctx.build_context_pack(project)
    assert '### D-001 |' not in baseline
    before = files(project)
    focused, meta = ctx.build_context_pack(project, query='brand narrative user agency')
    assert '### D-001 |' in focused
    assert 'D-001' in meta['task_focus']['current_ids']
    assert 'Review the local draft.' in focused and 'Never publish without approval.' in focused
    assert meta['current_action'] == baseline_meta['current_action']
    assert meta['chars'] == len(focused) <= 16000
    assert ctx.build_context_pack(project) == (baseline, baseline_meta)
    assert files(project) == before


def test_noncurrent_history_and_reversal_overlap_do_not_grant_authority(project):
    before = files(project)
    content, meta = ctx.build_context_pack(project, query='cloud migration funding budget')
    assert 'D-002' not in meta['task_focus']['current_ids']
    assert 'Non-current history' in content and 'status=superseded' in content
    assert 'No condition is confirmed met' in content
    assert meta['task_focus']['formal_state_changed'] is False
    assert files(project) == before


def test_existing_source_receipt_is_linked_not_approved(project):
    from flg.core.task_focus import select_decisions
    focus = select_decisions((project / 'DECISIONS.md').read_text(), 'funding budget')
    view = {'items': [{'receipt_id': 'review-example', 'binding': 'revalidation_required',
             'needs_review': True, 'judgments': [{'id': 'D-003'}]}], 'errors': []}
    notice = ctx._focus_navigation(project, 'funding budget', focus, view)
    assert 'review-example' in notice and 'revalidation_required' in notice
    assert 'Review only; formal state unchanged' in notice
    assert 'No condition is confirmed met' in notice


@pytest.mark.parametrize('mode', ['manifest', 'work', 'invalid'])
def test_query_other_modes_fail_explicitly(project, mode):
    with pytest.raises(ValueError, match='resume'):
        ctx.build_context_pack(project, mode=mode, query='brand narrative')


def test_small_budget_abstains_without_overwriting_previous_output(project):
    output = project / 'query-pack.md'
    output.write_text('Previous reviewed view.', encoding='utf-8')
    result = CliRunner().invoke(app, ['context', '--query', 'brand narrative', '--budget', '400',
                                     '--output', 'query-pack.md'])
    assert result.exit_code == 1 and 'budget' in result.output.lower()
    assert output.read_text() == 'Previous reviewed view.'


def test_cli_writes_only_requested_derived_output(project):
    before = files(project)
    result = CliRunner().invoke(app, ['context', '--query', 'brand narrative', '--output', 'query-pack.md'])
    assert result.exit_code == 0, result.output
    after = files(project)
    assert all(after[name] == raw for name, raw in before.items())
    assert set(after) - set(before) == {'query-pack.md'}
    assert not (project / '.flg/task-continuity.json').exists()


def test_changed_ledger_between_selection_and_render_abstains(project, monkeypatch):
    original = ctx.read_file_safe
    reads = 0
    def changed(path):
        nonlocal reads
        value = original(path)
        if path.name == 'DECISIONS.md':
            reads += 1
            if reads > 1:
                return value + '\nChanged during reading.\n'
        return value
    monkeypatch.setattr(ctx, 'read_file_safe', changed)
    with pytest.raises(ValueError, match='changed during task selection'):
        ctx.build_context_pack(project, query='brand narrative')


def test_source_review_count_includes_noncurrent_history(project, monkeypatch):
    view = {'items': [{'receipt_id': 'historical-review', 'binding': 'revalidation_required',
            'needs_review': True, 'judgments': [{'id': 'D-002'}]}], 'errors': [], 'state_sha256': 'synthetic'}
    monkeypatch.setattr('flg.core.source_receipts.context_notice', lambda root: ('', view))
    content, meta = ctx.build_context_pack(project, query='cloud migration')
    assert 'historical-review' in content
    assert meta['task_focus']['source_reviews'] == 1


@pytest.mark.parametrize('status', ['accepted', 'active'])
def test_evidence_reference_keeps_query_status(project, status):
    (project / 'DECISIONS.md').write_text(decision('D-001', 'Brand narrative', 'Keep user agency.', status), encoding='utf-8')
    content, meta = ctx.build_context_pack(project, query='brand narrative')
    assert f'- Status: {status}' in content
    assert f'status: {status}' in content.split('## Evidence References', 1)[1]


def test_ledger_drift_during_health_check_abstains(project, monkeypatch):
    original = ctx.validate_project
    def concurrent(root):
        value = original(root)
        path = root / 'DECISIONS.md'
        path.write_text(path.read_text().replace('confirmed', 'superseded'), encoding='utf-8')
        return value
    monkeypatch.setattr(ctx, 'validate_project', concurrent)
    with pytest.raises(ValueError, match='changed during task selection'):
        ctx.build_context_pack(project, query='brand narrative')


def test_query_does_not_silently_drop_seventh_constraint(project):
    path = project / 'SNAPSHOT.md'
    path.write_text(path.read_text() + '\n' + '\n'.join(f'- Boundary number {n}.' for n in range(2, 10)), encoding='utf-8')
    content, _ = ctx.build_context_pack(project, query='brand narrative')
    assert 'Boundary number 9.' in content


def test_query_fallback_constraint_source_not_silently_clipped(project):
    path = project / 'SNAPSHOT.md'
    path.write_text(path.read_text().split('## Hard Constraints')[0], encoding='utf-8')
    (project / 'CONSTRAINTS.md').write_text('# Constraints\n' + 'Retain this limitation. ' * 40 + '\nFinal boundary sentinel.', encoding='utf-8')
    content, _ = ctx.build_context_pack(project, query='brand narrative')
    assert 'Final boundary sentinel.' in content
