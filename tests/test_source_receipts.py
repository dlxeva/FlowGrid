"""Synthetic evidence, fresh process recovery, and unchanged formal state."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from flg.cli import app
from flg.commands.context import build_context_pack
from flg.core import source_receipts as sr

runner = CliRunner()
LEDGER = '''# Decisions

## D-001 | Validate the pilot before rollout

### Status
confirmed

### Final Decision
Use a small pilot; rollout is not approved.

### Decision Rationale
We need actual outcomes before committing resources.
'''


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app,['init','Synthetic Continuity']).exit_code == 0
    (tmp_path/'DECISIONS.md').write_text(LEDGER,encoding='utf-8')
    path = tmp_path/'sources/meetings/pilot/transcript.md'
    path.parent.mkdir(parents=True)
    path.write_text('User: Try a larger pilot; rollout remains unapproved.\nAssistant: We can compare outcomes.\nUnreviewed topic.\n',encoding='utf-8')
    (tmp_path/'work.md').write_text('Pilot work is accepted; results are still awaited.\n',encoding='utf-8')
    return tmp_path


def record(root):
    source = 'sources/meetings/pilot/transcript.md'
    quote = (root/source).read_text(encoding='utf-8').splitlines()[0]
    return {'id':'pilot-review','verified_at':'2026-01-12','status':'partial',
        'source':{'path':source,'quote':quote,'sha256':sr.digest((root/source).read_bytes())},
        'targets':[{'path':'work.md','anchor':'results are still awaited',
                    'sha256':sr.digest((root/'work.md').read_bytes())}],
        'remaining':['Only one excerpt reviewed; actual results and approval remain open.'],
        'continuity':{'schema_version':1,'coverage':'excerpt',
            'spans':[{'start':1,'end':1,'quote':quote,'attribution':'User, direct statement; no inferred identity'}],
            'judgments':[{'id':'D-001','basis_sha256':sr.digest(sr.decision_blocks(root)['D-001']),
                'span':0,'disposition':'implementation_changed','before':'Use a small pilot',
                'after':'Pilot scope can be revised; rollout remains unapproved.',
                'reason':'Explicit user evidence changes implementation conditions.',
                'next_action':'Review the accepted pilot results before proposing rollout.'}]}}


def apply(root, value=None):
    return sr.register(root,value or record(root),sr.load(root)[1])


def test_crlf_source_quotes_use_lf_locators_but_hash_original_bytes(project):
    item=record(project);source=project/item['source']['path']
    source.write_bytes(source.read_bytes().replace(b'\n',b'\r\n'))
    lines=source.read_bytes().decode().splitlines()
    quote='\n'.join(lines[:2])
    item['source'].update(sha256=sr.digest(source.read_bytes()),quote=quote)
    item['continuity']['spans'][0].update(end=2,quote=quote)
    assert apply(project,item)['validation']=='current'


def test_reader_compares_descriptor_metadata_without_mixing_path_stat(project):
    from types import SimpleNamespace
    original=os.fstat
    def crt_style(fd):
        info=original(fd)
        return SimpleNamespace(st_mode=info.st_mode,st_dev=info.st_dev+1,
            st_ino=info.st_ino+1,st_size=info.st_size,
            st_mtime_ns=info.st_mtime_ns//1000*1000,
            st_ctime_ns=info.st_ctime_ns//1000*1000)
    with patch.object(os,'fstat',side_effect=crt_style):
        assert sr.read_bytes(project,'work.md')==(project/'work.md').read_bytes()


def test_registration_and_reverse_lookup_preserve_formal_documents(project):
    protected = {p:(project/p).read_bytes() for p in ['DECISIONS.md','SNAPSHOT.md','work.md']}
    result = apply(project)
    assert result['validation']=='current' and result['formal_state_changed'] is False
    source=record(project)['source']['path']
    assert sr.trace(project,source)['items'][0]['receipt_id']=='pilot-review'
    reverse=sr.trace(project,'work.md',receipt_id='pilot-review')
    assert reverse['items'][0]['source_path']==source
    assert reverse['items'][0]['recorded_stage']=='partial'
    assert protected=={p:(project/p).read_bytes() for p in protected}


@pytest.mark.parametrize('mode',['resume','manifest','work'])
def test_context_surfaces_review_in_every_mode(project,mode):
    if mode=='work':
        state_path=project/'.flg/state.json'; state=json.loads(state_path.read_text())
        state['work_source']={'path':'work.md'}
        state_path.write_text(json.dumps(state),encoding='utf-8')
    apply(project)
    body,meta=build_context_pack(project,mode=mode)
    assert '## Source Review' in body and 'D-001' in body
    assert 'flg source pending' in body and meta['source_continuity']['review_count']==1


def test_small_budget_refuses_to_drop_current_work_or_review(project):
    apply(project)
    with pytest.raises(ValueError,match='budget'):
        build_context_pack(project,budget=100)


def test_handoff_and_export_keep_source_review_visible(project):
    from flg.commands.handoff import generate_handoff_summary
    apply(project)
    assert 'Source Review' in generate_handoff_summary(project)
    result=runner.invoke(app,['export-handoff','--output','handoff.md'])
    assert result.exit_code==0,result.output
    assert 'Source Review' in (project/'handoff.md').read_text(encoding='utf-8')


@pytest.mark.parametrize('name',['source','target','judgment'])
def test_byte_drift_hides_old_candidate_and_retry_preserves_history(project,name):
    item=record(project); apply(project,item); before=(project/sr.RECEIPTS).read_bytes()
    path=project/({'source':item['source']['path'],'target':'work.md','judgment':'DECISIONS.md'}[name])
    path.write_bytes(path.read_bytes()+b'\nChanged evidence.\n')
    view=sr.collect(project); entry=view['items'][0]
    assert entry['binding']=='revalidation_required' and entry['needs_review']
    assert 'next_action' not in entry['judgments'][0]
    result=sr.register(project,item,'old-cas-for-exact-retry')
    assert result['receipt']=='already_registered' and result['validation']=='revalidation_required'
    assert (project/sr.RECEIPTS).read_bytes()==before


def test_idempotent_transport_retry_and_content_conflict(project):
    item=record(project);apply(project,item)
    retry=deepcopy(item);retry.update(id='new-transport-id',verified_at='2026-01-13')
    assert sr.register(project,retry,'old')['receipt_id']==item['id']
    assert len(sr.load(project)[0]['receipts'])==1
    changed=deepcopy(item);changed['continuity']['judgments'][0]['after']='Different claim'
    with pytest.raises(ValueError,match='different content'):
        sr.register(project,changed,sr.load(project)[1])


def test_cas_conflict_keeps_source_state_and_no_new_index(project):
    with pytest.raises(ValueError,match='conflict'):
        sr.register(project,record(project),'0'*64)
    assert not (project/sr.RECEIPTS).exists()


@pytest.mark.parametrize('mutation',['excerpt_absorbed','bad_quote','missing_attribution','out_of_range','false_full','target_missing','target_hash','wrong_before','wrong_basis','promotion'])
def test_invalid_processing_and_approval_claims_are_refused(project,mutation):
    item=record(project);meta=item['continuity'];j=meta['judgments'][0]
    if mutation=='excerpt_absorbed':item.update(status='absorbed',remaining=[])
    if mutation=='bad_quote':meta['spans'][0]['quote']='Fabricated quote'
    if mutation=='missing_attribution':meta['spans'][0]['attribution']=''
    if mutation=='out_of_range':meta['spans'][0]['end']=90
    if mutation=='false_full':meta['coverage']='full'
    if mutation=='target_missing':item['targets'][0]['anchor']='No such evidence'
    if mutation=='target_hash':item['targets'][0]['sha256']='0'*64
    if mutation=='wrong_before':j['before']='Never stated'
    if mutation=='wrong_basis':j['basis_sha256']='0'*64
    if mutation=='promotion':j['disposition']='confirmed'
    with pytest.raises(ValueError):apply(project,item)
    assert not (project/sr.RECEIPTS).exists()


def test_full_scope_and_valid_targets_without_impact_are_quiet(project):
    item=record(project);meta=item['continuity'];text=(project/item['source']['path']).read_text(encoding='utf-8')
    meta.update(coverage='full',spans=[{'start':1,'end':3,'quote':text.rstrip('\n'),'attribution':'User and Assistant labels retained'}],judgments=[],no_judgment_reason='Routine verification only')
    item.update(status='absorbed',remaining=[])
    invalid=deepcopy(item);invalid['targets']=[]
    with pytest.raises(ValueError,match='target evidence'):apply(project,invalid)
    apply(project,item)
    assert sr.context_notice(project)[0]==''


@pytest.mark.parametrize('outcome',['shown','completed','rejected'])
def test_acknowledgments_and_drift_do_not_revive_old_actions(project,outcome):
    item=record(project);apply(project,item)
    sr.acknowledge(project,item['id'],outcome,sr.load(project)[1],'Actual display or owner disposition')
    view=sr.collect(project)['items'][0]
    assert not view['reminder_due']
    assert view['needs_review']==(outcome=='shown')
    if outcome!='shown':assert sr.context_notice(project)[0]==''
    sr.register(project,item,'old')
    assert sr.collect(project)['items'][0]['acknowledgment']==outcome
    (project/'work.md').write_text('New work evidence',encoding='utf-8')
    view=sr.collect(project)['items'][0]
    assert view['needs_review'] and 'next_action' not in view['judgments'][0]


def test_retained_judgment_and_unrelated_filter_are_quiet(project):
    item=record(project);item['continuity']['judgments'][0]['disposition']='retain'
    apply(project,item)
    assert sr.context_notice(project)[0]==''
    assert sr.collect(project,'D-002')['items']==[]


def test_no_judgment_drift_stays_visible(project):
    item=record(project);item['continuity'].update(judgments=[],no_judgment_reason='No decision affected')
    apply(project,item);assert sr.context_notice(project)[0]==''
    (project/item['source']['path']).write_text('New input',encoding='utf-8')
    assert 'Source Review' in sr.context_notice(project)[0]


@pytest.mark.parametrize('field',['spans','judgments','coverage'])
def test_corrupt_receipt_is_visible_without_formal_write(project,field):
    item=record(project);apply(project,item)
    data,_=sr.load(project);data['receipts'][0]['continuity'][field]=None
    (project/sr.RECEIPTS).write_text(json.dumps(data),encoding='utf-8')
    view=sr.collect(project)
    assert view['errors'] or any(i['binding']=='revalidation_required' for i in view['items'])
    assert sr.context_notice(project)[0]


def test_original_parent_binding_is_separate_and_no_same_name_inference(project):
    parent=project/'original.txt';parent.write_text('original input',encoding='utf-8')
    item=record(project);item['source']['derived_from']=[{'path':'original.txt','sha256':sr.digest(parent.read_bytes()),'relation':'transcribed_from'}]
    apply(project,item);parent.write_text('changed original',encoding='utf-8')
    view=sr.trace(project,item['source']['path'])['items'][0]
    assert view['matches'][0]['version_binding']=='current'
    assert view['parents'][0]['version_binding']=='stale'
    assert sr.trace(project,'original.txt')['total']==1


def test_exact_reverse_lookup_past_display_cap_and_legacy_unchanged(project):
    items=[]
    for number in range(15):
        item=record(project);item['id']=f'review-{number}'
        source=project/f'sources/meetings/pilot/transcript-{number}.md'
        source.write_bytes((project/item['source']['path']).read_bytes())
        item['source']['path']=source.relative_to(project).as_posix()
        apply(project,item);items.append(item)
    assert sr.trace(project,'work.md')['omitted']==3
    assert sr.trace(project,'work.md','review-14')['items'][0]['receipt_id']=='review-14'


def test_failed_atomic_write_can_retry_without_false_completion(project):
    item=record(project)
    with patch.object(sr,'atomic_write_text',side_effect=OSError('write failed')):
        with pytest.raises(OSError):apply(project,item)
    assert not (project/sr.RECEIPTS).exists()
    assert apply(project,item)['receipt']=='registered'


def test_paths_and_duplicate_json_are_rejected(project):
    for path in ('../outside.md','/absolute.md','C:/outside.md','sources\\outside.md','work.md\nignored'):
        with pytest.raises(ValueError):sr.read_bytes(project,path)
    with pytest.raises(ValueError,match='Duplicate'):sr.parse_json('{"id":1,"id":2}')
    alias=project/'alias.md'
    try:alias.symlink_to(project/'work.md')
    except OSError:pytest.skip('Host cannot create symlinks')
    item=record(project);item['targets'][0]['path']='alias.md'
    with pytest.raises(ValueError,match='Symlink'):apply(project,item)


def test_cli_prepare_record_pending_and_new_process_resume(project):
    item=record(project);item['continuity']['spans'][0].pop('quote')
    (project/'review.json').write_text(json.dumps(item),encoding='utf-8')
    prepared=runner.invoke(app,['source','prepare','--input','review.json','--output','candidate.json'])
    assert prepared.exit_code==0,prepared.output
    stored=runner.invoke(app,['source','record','--input','candidate.json','--expected-sha256','absent'])
    assert stored.exit_code==0,stored.output
    assert runner.invoke(app,['source','prepare','--input','review.json','--output','candidate.json']).exit_code==2
    pending=runner.invoke(app,['source','pending','--reminders'])
    assert len(json.loads(pending.output)['items'])==1
    # A fresh process reads only the frozen project state, not this Python call.
    repo=Path(__file__).resolve().parents[1]
    env=dict(os.environ,PYTHONPATH=str(repo/'src'),PYTHONUTF8='1')
    result=subprocess.run([sys.executable,'-c','from flg.cli import app; app()',
        'context','--mode','manifest','--print'],cwd=project,env=env,capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,result.stderr+result.stdout
    assert 'Source Review' in result.stdout and 'D-001' in result.stdout


def test_read_only_queries_do_not_create_project_state(project):
    before={p.relative_to(project):p.read_bytes() for p in project.rglob('*') if p.is_file()}
    sr.collect(project);sr.context_notice(project);sr.trace(project,'work.md')
    after={p.relative_to(project):p.read_bytes() for p in project.rglob('*') if p.is_file()}
    assert before==after


def test_transport_metadata_cannot_reactivate_rejected_review(project):
    item=record(project);apply(project,item)
    sr.acknowledge(project,item['id'],'rejected',sr.load(project)[1],'Rejected by owner')
    changed=deepcopy(item);changed.update(id='new-transport',verified_at='2026-01-13',transport_request_id='request-2')
    with pytest.raises(ValueError,match='Unknown receipt fields'):apply(project,changed)
    changed.pop('transport_request_id');changed['scope']='A refreshed display caption'
    assert apply(project,changed)['receipt']=='already_registered'
    assert sr.context_notice(project)[0]==''


def test_reordered_work_references_do_not_reactivate_rejected_review(project):
    item=record(project);other=project/'other-work.md';other.write_text('Other work is accepted; await results.')
    item['targets'].append({'path':'other-work.md','sha256':sr.digest(other.read_bytes()),'anchor':'await results'})
    apply(project,item);sr.acknowledge(project,item['id'],'rejected',sr.load(project)[1],'Owner rejected')
    retry=deepcopy(item);retry['id']='permuted';retry['targets'].reverse()
    assert apply(project,retry)['receipt']=='already_registered'
    assert sr.context_notice(project)[0]==''


def test_source_review_does_not_allow_budget_to_hide_current_action(project):
    snapshot=project/'SNAPSHOT.md'
    snapshot.write_text('# Snapshot\n\n## Current Core Goal\n\n'+'Goal '*300+'\n\n## Next Highest Priority Action\n\nInspect the accepted results.\n',encoding='utf-8')
    apply(project)
    with pytest.raises(ValueError,match='budget'):
        build_context_pack(project,budget=400)


def test_doctor_does_not_hide_corrupt_processing_state(project):
    (project/sr.RECEIPTS).write_text('{broken JSON',encoding='utf-8')
    result=runner.invoke(app,['doctor','--strict'])
    assert result.exit_code==1
    assert 'processing_source_bindings' in result.output


@pytest.mark.parametrize('source_kind',['self','parent','json'])
def test_source_cannot_certify_its_own_absorption_or_raw_metadata(project,source_kind):
    item=record(project);meta=item['continuity'];source=project/item['source']['path']
    if source_kind=='json':
        alternate=source.with_suffix('.json');alternate.write_bytes(source.read_bytes());item['source']['path']=alternate.relative_to(project).as_posix()
    meta.update(coverage='full',spans=[{'start':1,'end':3,'quote':source.read_text().rstrip('\n'),'attribution':'Original labels retained'}],judgments=[],no_judgment_reason='Routine archive')
    item.update(status='absorbed',remaining=[])
    if source_kind=='self':item['targets']=[{'path':item['source']['path'],'sha256':item['source']['sha256'],'anchor':'User:'}]
    if source_kind=='parent':
        original=project/'original.md';original.write_text('Original before transcription')
        item['source']['derived_from']=[{'path':'original.md','sha256':sr.digest(original.read_bytes()),'relation':'transcribed_from'}]
        item['targets']=[{'path':'original.md','sha256':sr.digest(original.read_bytes()),'anchor':'Original'}]
    with pytest.raises(ValueError):apply(project,item)


def test_stale_review_resolves_through_current_successor_without_reopening(project):
    old=record(project);apply(project,old)
    sr.acknowledge(project,old['id'],'completed',sr.load(project)[1],'Initial review done')
    (project/'work.md').write_text('Pilot revised; results are still awaited.\n')
    new=record(project);new['id']='revalidated-review';apply(project,new)
    sr.acknowledge(project,new['id'],'completed',sr.load(project)[1],'New evidence reviewed')
    assert sr.collect(project)['items'][0]['needs_review']
    result=sr.resolve(project,old['id'],new['id'],sr.load(project)[1],'Revalidated updated implementation')
    assert result['resolution']=='recorded' and sr.context_notice(project)[0]==''
    data,version=sr.load(project)
    assert data['receipts'][0]==old and data['acknowledgments'][old['id']]['history'][0]['event']=='completed'
    assert sr.resolve(project,old['id'],new['id'],version,'Revalidated updated implementation')['resolution']=='already_recorded'
    (project/'work.md').write_text('Later implementation change.\n')
    view=sr.collect(project)
    assert not view['items'][0]['needs_review'] and view['items'][1]['needs_review']
    assert all('next_action' not in j for i in view['items'] for j in i['judgments'])
    with pytest.raises(ValueError):sr.resolve(project,new['id'],old['id'],sr.load(project)[1],'Would create a cycle')


def test_changed_source_can_resolve_through_full_current_review(project):
    old = record(project)
    apply(project, old)
    source = project / old['source']['path']
    source.write_text('New introduction.\n' + source.read_text())
    new = record(project)
    new['id'] = 'full-current-review'
    new['continuity'].update(coverage='full', spans=[{
        'start': 1, 'end': 4, 'quote': source.read_text().rstrip('\n'),
        'attribution': 'All original labels retained'}])
    apply(project, new)
    sr.acknowledge(project, new['id'], 'completed', sr.load(project)[1], 'All current source reviewed')
    assert sr.resolve(project, old['id'], new['id'], sr.load(project)[1],
                      'Complete replacement review')['resolution'] == 'recorded'
    assert sr.context_notice(project)[0] == ''


def test_resolution_requires_real_current_replacement_and_cannot_hide_other_work(project):
    first=record(project);apply(project,first)
    second=deepcopy(first);second['id']='wrong-scope';second['targets']=[]
    apply(project,second)
    with pytest.raises(ValueError,match='work references'):
        sr.resolve(project,first['id'],second['id'],sr.load(project)[1],'Incomplete replacement')
    with pytest.raises(ValueError):sr.resolve(project,first['id'],first['id'],sr.load(project)[1],'Self resolution')


def test_resolution_cannot_shrink_full_source_review_to_one_unchanged_line(project):
    old=record(project);source=project/old['source']['path']
    old['continuity'].update(coverage='full',spans=[{'start':1,'end':3,'quote':source.read_text().rstrip('\n'),'attribution':'All source labels retained'}])
    apply(project,old)
    source.write_text(source.read_text().replace('Unreviewed topic.','Changed implementation topic.'))
    new=record(project);new['id']='narrower';new['continuity']['judgments'][0]['disposition']='retain'
    apply(project,new)
    with pytest.raises(ValueError,match='smaller excerpt'):
        sr.resolve(project,old['id'],new['id'],sr.load(project)[1],'Cannot silently narrow coverage')
    assert sr.collect(project)['items'][0]['needs_review']


def test_resolution_cannot_skip_a_previously_reviewed_partial_range(project):
    old=record(project);source=project/old['source']['path']
    old['continuity']['spans'].append({'start':3,'end':3,'quote':'Unreviewed topic.','attribution':'Anonymous, role unknown'})
    apply(project,old)
    source.write_text(source.read_text().replace('Unreviewed topic.','Changed topic.'))
    new=record(project);new['id']='missing-range';apply(project,new)
    with pytest.raises(ValueError,match='every prior reviewed'):
        sr.resolve(project,old['id'],new['id'],sr.load(project)[1],'Old scope must remain visible')


@pytest.mark.parametrize('edit', ['insert', 'delete'])
def test_shifted_source_lines_cannot_resolve_old_excerpt(project, edit):
    source = project / record(project)['source']['path']
    source.write_text('Intro.\nPreviously reviewed topic.\nOther topic.\n')
    old = record(project)
    old['source']['quote'] = 'Previously reviewed topic.'
    old['continuity']['spans'] = [{'start': 2, 'end': 2, 'quote': old['source']['quote'],
                                 'attribution': 'Anonymous, role unknown'}]
    apply(project, old)
    source.write_text(('Inserted.\n' + source.read_text()) if edit == 'insert'
                      else source.read_text().removeprefix('Intro.\n'))
    new = record(project)
    new['id'] = 'shifted-review'
    new['source']['quote'] = source.read_text().splitlines()[1]
    new['continuity']['spans'] = [{'start': 2, 'end': 2, 'quote': new['source']['quote'],
                                 'attribution': 'Anonymous, role unknown'}]
    apply(project, new)
    sr.acknowledge(project, new['id'], 'completed', sr.load(project)[1], 'Only this excerpt reviewed')
    before = (project / sr.RECEIPTS).read_bytes()
    with pytest.raises(ValueError, match='source version'):
        sr.resolve(project, old['id'], new['id'], sr.load(project)[1], 'Same numeric lines')
    assert (project / sr.RECEIPTS).read_bytes() == before
    assert sr.collect(project)['items'][0]['needs_review']


@pytest.mark.parametrize('name,quote,disposition,after',[
    ('parameter-a','User: Estimate a larger pilot; actual attendance is unverified.','implementation_changed','The pilot estimate can change; actual attendance still needs evidence.'),
    ('date-b','User: The earliest review window is next month; it is not booked.','implementation_changed','Use the earliest window for planning; confirm the actual date.'),
    ('reject-a','User: Reject the old outreach; keep the draft local.','replacement_candidate','A replacement is proposed; no external action is authorized.'),
    ('reopen-b','User: Reopen the pilot comparison; rollout is still undecided.','replacement_candidate','Recompare options before any new rollout decision.'),
    ('discussion-a','User: Could a larger pilot help? We have not decided.','unresolved','The larger pilot remains a discussion question.'),
    ('discussion-b','User: A shorter review might help; please test the assumption.','unresolved','Review duration remains a hypothesis to test.'),
    ('completed-a','User: I already sent the review request; await their response.','supplement','Preserve the completed sending step; inspect the response later.'),
    ('accepted-b','User: They accepted the pilot work and will send results.','supplement','Inspect accepted work when results arrive; do not reissue the request.'),
])
def test_eight_continuation_boundaries_keep_host_judgments_as_candidates(project,name,quote,disposition,after):
    item=record(project);path=project/item['source']['path'];path.write_text(quote+'\nOther topics not reviewed.\n',encoding='utf-8')
    item.update(id=name);item['source'].update(quote=quote,sha256=sr.digest(path.read_bytes()))
    item['continuity']['spans'][0]['quote']=quote
    j=item['continuity']['judgments'][0];j.update(disposition=disposition,after=after)
    formal=(project/'DECISIONS.md').read_bytes();apply(project,item)
    body,meta=build_context_pack(project)
    assert 'D-001' in body and meta['source_continuity']['review_count']==1
    visible=sr.collect(project)['items'][0]
    assert visible['recorded_stage']=='partial' and visible['judgments'][0]['after']==after
    assert visible['spans'][0]['quote']==quote
    assert (project/'DECISIONS.md').read_bytes()==formal
