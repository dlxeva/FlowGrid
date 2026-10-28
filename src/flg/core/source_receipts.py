"""Version-bound processing declarations and derived review notices.

Only the processing receipt is written. Formal judgments and work documents stay
under their existing review paths. No semantic extraction runs in this module.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any

from .operations import atomic_write_text, project_operation_lock

RECEIPTS = '.flg/processing-receipts.json'
DISPOSITIONS = {'retain', 'supplement', 'implementation_changed', 'replacement_candidate', 'unresolved'}
PENDING = {'implementation_changed', 'replacement_candidate', 'unresolved'}
READ_ERRORS = (ValueError, OSError, UnicodeError, KeyError, TypeError)


def digest(raw: bytes | str) -> str:
    return sha256(raw.encode('utf-8') if isinstance(raw, str) else raw).hexdigest()


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_hash(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def relative(value: Any) -> str:
    require(nonempty(value) and '\\' not in value and ':' not in value
            and not any(ord(c) < 32 or ord(c) == 127 for c in value), 'Expected a project-relative file path')
    require(not PurePosixPath(value).is_absolute() and
            all(part not in ('', '.', '..') for part in value.split('/')), 'Unsafe project-relative path')
    return value


def checked_path(root: Path, value: str) -> Path:
    relative(value)
    require(not root.is_symlink(), 'Symlinked project roots are unsupported')
    current = root.resolve(strict=True)
    for part in value.split('/'):
        current = current / part
        require(not current.is_symlink(), 'Symlinked source/state paths are unsupported')
    return current


def read_bytes(root: Path, value: str) -> bytes:
    path = checked_path(root, value)
    # NONBLOCK prevents a FIFO from hanging before the regular-file check.
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as handle:
        before = os.fstat(handle.fileno())
        require(stat.S_ISREG(before.st_mode), 'Expected a regular source/state file')
        raw = handle.read()
        after = os.fstat(handle.fileno())
    checked_path(root, value)
    final = path.stat()
    signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    require(signature(before) == signature(after) == signature(final), 'File changed while reading; retry')
    return raw


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON field')
        result[key] = value
    return result


def parse_json(raw: bytes | str) -> dict:
    result = json.loads(raw, object_pairs_hook=_pairs,
                        parse_constant=lambda _: require(False, 'Nonstandard JSON constant'))
    require(isinstance(result, dict), 'Expected a JSON object')
    return result


def load(root: Path) -> tuple[dict, str]:
    try:
        raw = read_bytes(root, RECEIPTS)
    except FileNotFoundError:
        return {'schema_version': 1, 'receipts': []}, 'absent'
    data = parse_json(raw)
    require(type(data.get('schema_version')) is int and data['schema_version'] == 1,
            'Unsupported processing receipt schema')
    require(isinstance(data.get('receipts'), list), 'receipts must be a list')
    seen = set()
    for record in data['receipts']:
        require(isinstance(record, dict) and nonempty(record.get('id'))
                and record['id'] not in seen, 'Missing or duplicate receipt ID')
        seen.add(record['id'])
    require(isinstance(data.get('acknowledgments', {}), dict), 'Invalid receipt acknowledgments')
    return data, digest(raw)


def decision_blocks(root: Path) -> dict[str, str]:
    text = read_bytes(root, 'DECISIONS.md').decode('utf-8')
    headings = list(re.finditer(r'^#{2,3} (D-\d+)\b[^\n]*', text, re.M))
    result = {}
    for index, heading in enumerate(headings):
        require(heading[1] not in result, 'Duplicate judgment ID')
        end = headings[index+1].start() if index+1 < len(headings) else len(text)
        result[heading[1]] = text[heading.start():end].strip()
    return result


def _source(root: Path, source: dict) -> str:
    require(isinstance(source, dict) and valid_hash(source.get('sha256')), 'Source SHA256 is required')
    require(PurePosixPath(relative(source.get('path'))).suffix.lower() in {'.md','.txt'},
            'Primary sources must be reviewable Markdown or text, not raw response metadata')
    from .source_inventory import describe
    discovered = describe(root,source['path'])
    require(discovered is None or discovered['review_eligible'], 'Raw responses are not reviewable primary sources')
    raw = read_bytes(root, source.get('path'))
    require(digest(raw) == source['sha256'], 'Source version changed; reread the source')
    text = raw.decode('utf-8').replace('\r\n','\n').replace('\r','\n')
    require(nonempty(source.get('quote')) and source['quote'] in text, 'Source quote does not match original bytes')
    require('quote_sha256' not in source or source['quote_sha256'] == digest(source['quote']), 'Source quote hash mismatch')
    parents = source.get('derived_from', [])
    require(isinstance(parents, list) and len(parents) <= 12, 'At most 12 explicit source parents are supported')
    seen = {source['path']}
    for parent in parents:
        require(isinstance(parent, dict) and set(parent) == {'path','sha256','relation'}, 'Invalid source parent')
        require(parent['path'] not in seen and valid_hash(parent['sha256']), 'Invalid or duplicate source parent')
        require(parent['relation'] in {'extracted_from','transcribed_from','summarized_from'}, 'Invalid parent relation')
        require(digest(read_bytes(root, parent['path'])) == parent['sha256'], 'Parent source version changed')
        seen.add(parent['path'])
    return text


def validate(root: Path, record: dict) -> None:
    require(isinstance(record, dict) and nonempty(record.get('id')) and len(record['id']) <= 240,
            'A bounded receipt ID is required')
    require(nonempty(record.get('verified_at')), 'verified_at is required')
    require(record.get('status') in {'partial','absorbed','waiting_evidence'}, 'Invalid processing stage')
    remaining = record.get('remaining')
    require(isinstance(remaining, list) and all(nonempty(item) for item in remaining), 'Invalid remaining work')
    require((record['status'] == 'absorbed') == (not remaining), 'Processing stage and remaining work disagree')
    meta = record.get('continuity')
    require(isinstance(meta, dict) and type(meta.get('schema_version')) is int
            and meta['schema_version'] == 1, 'continuity schema_version=1 is required')
    require(meta.get('coverage') in {'excerpt','full'}, 'coverage must be excerpt or full')
    text = _source(root, record.get('source'))
    lines = text.splitlines()
    spans = meta.get('spans')
    require(isinstance(spans, list) and bool(spans), 'Explicit reviewed spans are required')
    previous, reviewed = 0, 0
    for span in spans:
        require(isinstance(span, dict), 'Each reviewed span must be an object')
        start, end = span.get('start'), span.get('end')
        require(type(start) is int and type(end) is int and previous < start <= end <= len(lines),
                'Reviewed spans must be ordered, nonoverlapping, and inside the source')
        require(span.get('quote') == '\n'.join(lines[start-1:end]), 'Reviewed span must match exact source lines')
        require(nonempty(span.get('attribution')), 'Reviewed span attribution is required')
        previous, reviewed = end, reviewed + end-start+1
    require(any(record['source']['quote'] in span['quote'] for span in spans), 'Primary quote must be inside the reviewed scope')
    require(meta['coverage'] != 'full' or reviewed == len(lines), 'Full coverage must include every source line')
    require(meta['coverage'] != 'excerpt' or record['status'] != 'absorbed', 'Excerpt review must remain partial')
    targets = record.get('targets')
    require(isinstance(targets, list), 'targets must be a list')
    require((meta['coverage'] != 'full' and record['status'] != 'absorbed') or bool(targets), 'Full review needs target evidence')
    for target in targets:
        require(isinstance(target, dict) and valid_hash(target.get('sha256')), 'Target SHA256 is required')
        raw = read_bytes(root, target.get('path'))
        source_paths = [record['source']['path'], *[p['path'] for p in record['source'].get('derived_from',[])]]
        target_stat = checked_path(root,target['path']).stat()
        require(all(target['path'] != source_path and
                (target_stat.st_dev,target_stat.st_ino) !=
                (checked_path(root,source_path).stat().st_dev,checked_path(root,source_path).stat().st_ino)
                for source_path in source_paths), 'A source or its original cannot certify its own absorption')
        require(digest(raw) == target['sha256'], 'Target version changed; reread affected work')
        require(nonempty(target.get('anchor')) and target['anchor'] in
                raw.decode('utf-8').replace('\r\n','\n').replace('\r','\n'), 'Target anchor is missing')
    judgments = meta.get('judgments')
    require(isinstance(judgments, list), 'judgments must be a list')
    require(bool(judgments) or nonempty(meta.get('no_judgment_reason')), 'Explain when no judgment is affected')
    blocks = decision_blocks(root) if judgments else {}
    seen = set()
    for judgment in judgments:
        require(isinstance(judgment, dict), 'Invalid judgment impact')
        ident = judgment.get('id')
        require(isinstance(ident, str) and re.fullmatch(r'D-\d+', ident) and ident not in seen, 'Invalid or duplicate judgment ID')
        seen.add(ident)
        require(judgment.get('disposition') in DISPOSITIONS, 'Invalid disposition; formal approval is unsupported')
        for field in ('before','after','reason','next_action'):
            require(nonempty(judgment.get(field)), 'Judgment impact needs ' + field)
        require(ident in blocks and valid_hash(judgment.get('basis_sha256')) and
                digest(blocks[ident]) == judgment['basis_sha256'], 'Judgment basis changed; reread it')
        require(judgment['before'] in blocks[ident], 'Previous condition must quote the actual judgment')
        require(type(judgment.get('span')) is int and 0 <= judgment['span'] < len(spans), 'Judgment must reference a reviewed span')
        require(judgment['disposition'] not in PENDING or record['status'] != 'absorbed', 'Pending judgment review cannot be absorbed')


def prepare(root: Path, review: dict) -> dict:
    record = deepcopy(review)
    text = _source(root, record.get('source'))
    lines = text.splitlines()
    meta = record.get('continuity')
    require(isinstance(meta, dict) and isinstance(meta.get('spans'), list), 'Explicit spans required')
    for span in meta['spans']:
        require(isinstance(span, dict), 'Invalid span')
        start, end = span.get('start'), span.get('end')
        require(type(start) is int and type(end) is int and 1 <= start <= end <= len(lines), 'Invalid prepare range')
        quote = '\n'.join(lines[start-1:end])
        require('quote' not in span or span['quote'] == quote, 'Prepare cannot replace an incorrect supplied quote')
        span['quote'] = quote
    validate(root, record)
    return record


def _identity(record: dict) -> dict:
    # Immutable target evidence added by a project adapter is not a new claim.
    result = deepcopy(record)
    for target in result.get('targets', []):
        if isinstance(target, dict):
            target.pop('evidence_snapshot', None)
    return result


def _logical(record: dict) -> dict:
    value = _identity(record)
    # Transport IDs, dates, display captions and private adapter labels cannot
    # turn the same reviewed evidence into a fresh suggestion.
    meta = value.get('continuity', {})
    unordered = lambda values: sorted({json.dumps(v,sort_keys=True,ensure_ascii=False) for v in values})
    source={k:v for k,v in value.get('source',{}).items() if k not in {'quote','quote_sha256','derived_from'}}
    source['derived_from']=unordered(value.get('source',{}).get('derived_from',[]))
    continuity={k:v for k,v in meta.items() if k not in {'tasks','task_basis','judgments'}}
    continuity['judgments']=unordered(meta.get('judgments',[]))
    return {'status':value.get('status'),'remaining':unordered(value.get('remaining',[])),
            'targets':unordered(value.get('targets',[])),'source':source,'continuity':continuity}


def _new_shape(record: dict) -> None:
    require(not set(record)-{'id','verified_at','status','source','targets','remaining','continuity','scope','priority'},
            'Unknown receipt fields; transport metadata must stay outside the processing declaration')
    source=record.get('source')
    require(isinstance(source,dict) and not set(source)-{'path','sha256','quote','quote_sha256','derived_from'}, 'Unknown source fields')
    meta=record.get('continuity')
    require(isinstance(meta,dict) and not set(meta)-{'schema_version','coverage','spans','judgments','no_judgment_reason','tasks','task_basis'}, 'Unknown continuity fields')
    require(isinstance(meta.get('spans'),list) and isinstance(meta.get('judgments'),list)
            and isinstance(record.get('targets'),list), 'Review ranges, judgments, and targets must be lists')
    for span in meta.get('spans',[]):
        require(isinstance(span,dict) and not set(span)-{'start','end','quote','attribution'}, 'Unknown span fields')
    for judgment in meta.get('judgments',[]):
        require(isinstance(judgment,dict) and not set(judgment)-{'id','basis_sha256','span','disposition','before','after','reason','next_action'}, 'Unknown judgment fields')
    for target in record.get('targets',[]):
        require(isinstance(target,dict) and not set(target)-{'path','sha256','anchor','evidence_snapshot'}, 'Unknown target fields')


def register(root: Path, record: dict, expected: str) -> dict:
    require(isinstance(record, dict) and nonempty(record.get('id')), 'Receipt ID required')
    _new_shape(record)
    checked_path(root, RECEIPTS)
    with project_operation_lock(root):
        data, version = load(root)
        existing = next((r for r in data['receipts'] if r['id'] == record['id']), None)
        same_id = existing is not None
        if existing is None:
            existing = next((r for r in data['receipts'] if _logical(r) == _logical(record)), None)
        if existing is not None:
            require((_identity(existing) == _identity(record)) if same_id else
                    (_logical(existing) == _logical(record)), 'Receipt ID has different content; append a correction')
            result = {'receipt':'already_registered','receipt_id':existing['id']}
            record = existing
        else:
            require(version == expected, 'Receipt conflict; reread and merge before retrying')
            validate(root, record)
            data['receipts'].append(deepcopy(record))
            # Recheck the byte declarations immediately before replacing state.
            validate(root, record)
            atomic_write_text(checked_path(root, RECEIPTS), json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            result = {'receipt':'registered','receipt_id':record['id']}
    try:
        validate(root, record)
        result['validation'] = 'current'
    except READ_ERRORS as exc:
        result.update(validation='revalidation_required', reason=str(exc))
    result.update(formal_state_changed=False, state_sha256=load(root)[1])
    return result


def acknowledge(root: Path, receipt_id: str, event: str, expected: str, reason: str) -> dict:
    require(event in {'shown','completed','rejected'} and nonempty(reason), 'An acknowledgment outcome and reason are required')
    checked_path(root, RECEIPTS)
    with project_operation_lock(root):
        data, version = load(root)
        require(version == expected, 'Receipt conflict; reread before acknowledgment')
        record = next((r for r in data['receipts'] if r['id'] == receipt_id), None)
        require(record is not None and 'continuity' in record, 'Unknown continuity receipt')
        validate(root, record)
        identity = digest(json.dumps(_identity(record),sort_keys=True,ensure_ascii=False))
        acknowledgments = data.setdefault('acknowledgments', {})
        previous = acknowledgments.get(receipt_id)
        require(not previous or previous.get('event') not in {'completed','rejected','superseded'}
                or previous.get('event') == event, 'Closed receipt acknowledgments cannot be reopened')
        item = {'receipt_sha256':identity,'event':event,'reason':reason}
        if previous and {k:v for k,v in previous.items() if k!='history'} != item:
            item['history'] = [*previous.get('history',[]),{k:v for k,v in previous.items() if k!='history'}]
        elif previous:
            item = previous
        if previous != item:
            acknowledgments[receipt_id] = item
            validate(root, record)
            atomic_write_text(checked_path(root, RECEIPTS), json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    return {'receipt_id':receipt_id,'event':event,'formal_state_changed':False,'state_sha256':load(root)[1]}


def _replacement(old: dict, new: dict) -> None:
    require(old['id'] != new['id'], 'A receipt cannot resolve itself')
    require(old['source']['path'] == new['source']['path'], 'Replacement must review the same source')
    require({t['path'] for t in old['targets']} <= {t['path'] for t in new['targets']}, 'Replacement must cover prior work references')
    require({j['id'] for j in old['continuity']['judgments']} <=
            {j['id'] for j in new['continuity']['judgments']}, 'Replacement must cover prior judgments')
    require({p['path'] for p in old['source'].get('derived_from',[])} <=
            {p['path'] for p in new['source'].get('derived_from',[])}, 'Replacement must retain original source references')
    require(old['continuity']['coverage'] != 'full' or new['continuity']['coverage']=='full',
            'A full-source review cannot be resolved by a smaller excerpt')
    if new['continuity']['coverage'] != 'full':
        for span in old['continuity']['spans']:
            cursor=span['start']
            for candidate in new['continuity']['spans']:
                if candidate['end'] < cursor:continue
                if candidate['start'] > cursor:break
                cursor=candidate['end']+1
            require(cursor > span['end'],'Replacement must cover every prior reviewed line range')


def resolve(root: Path, receipt_id: str, replacement_id: str, expected: str, reason: str) -> dict:
    """Explicitly retire a stale processing claim through a current reviewed one."""
    require(nonempty(reason), 'Resolution reason is required')
    with project_operation_lock(root):
        data,version=load(root)
        require(version == expected, 'Receipt conflict; reread before resolving')
        by_id={r['id']:r for r in data['receipts']}
        old,new=by_id.get(receipt_id),by_id.get(replacement_id)
        require(old is not None and new is not None, 'Both processing receipts must exist')
        _replacement(old,new)
        # Only a newly inspected current receipt can retire the obsolete claim.
        validate(root,new)
        acks=data.setdefault('acknowledgments',{})
        seen={receipt_id}
        next_id=replacement_id
        while next_id in acks and acks[next_id].get('event')=='superseded':
            require(next_id not in seen, 'Circular receipt resolution')
            seen.add(next_id);next_id=acks[next_id].get('replacement_id')
        require(next_id not in seen, 'Circular receipt resolution')
        old_ack=acks.get(receipt_id)
        item={'receipt_sha256':digest(json.dumps(_identity(old),sort_keys=True,ensure_ascii=False)),
              'event':'superseded','reason':reason,'replacement_id':replacement_id,
              'replacement_sha256':digest(json.dumps(_identity(new),sort_keys=True,ensure_ascii=False))}
        if old_ack and {k:v for k,v in old_ack.items() if k!='history'} == item:
            return {'receipt_id':receipt_id,'replacement_id':replacement_id,'resolution':'already_recorded','formal_state_changed':False,'state_sha256':version}
        if old_ack:
            require(old_ack.get('event')!='superseded','An existing resolution cannot be rewritten')
            item['history']=[*old_ack.get('history',[]),{k:v for k,v in old_ack.items() if k!='history'}]
        acks[receipt_id]=item
        validate(root,new)
        atomic_write_text(checked_path(root,RECEIPTS),json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    return {'receipt_id':receipt_id,'replacement_id':replacement_id,'resolution':'recorded','formal_state_changed':False,'state_sha256':load(root)[1]}


def collect(root: Path, judgment_id: str | None = None) -> dict:
    try:
        data, version = load(root)
    except READ_ERRORS as exc:
        return {'items':[],'errors':[str(exc)],'state_sha256':'unreadable'}
    items, errors, legacy = [], [], 0
    by_id={r['id']:r for r in data['receipts']}
    for record in data['receipts']:
        if 'continuity' not in record:
            legacy += 1
            continue
        try:
            meta = record['continuity']
            require(isinstance(meta, dict) and isinstance(meta.get('judgments'), list), 'Malformed continuity record')
            require(all(isinstance(j, dict) and isinstance(j.get('id'),str) for j in meta['judgments']), 'Malformed judgment reference')
            if judgment_id and not any(j['id'] == judgment_id for j in meta['judgments']):
                continue
            binding, problem = 'current', None
            try:
                validate(root, record)
            except READ_ERRORS as exc:
                binding, problem = 'revalidation_required', str(exc)
            acknowledgment = data.get('acknowledgments', {}).get(record['id'])
            acknowledged = None
            if acknowledgment:
                require(isinstance(acknowledgment, dict) and acknowledgment.get('event') in {'shown','completed','rejected','superseded'}, 'Invalid acknowledgment')
                identity = digest(json.dumps(_identity(record),sort_keys=True,ensure_ascii=False))
                require(acknowledgment.get('receipt_sha256') == identity, 'Acknowledgment version conflict')
                acknowledged = acknowledgment['event']
                if acknowledged=='superseded':
                    successor=by_id.get(acknowledgment.get('replacement_id'))
                    require(successor is not None,'Missing replacement receipt')
                    _replacement(record,successor)
                    require(acknowledgment.get('replacement_sha256') == digest(json.dumps(_identity(successor),sort_keys=True,ensure_ascii=False)), 'Replacement version conflict')
                    seen_chain=set();current=record['id']
                    while current in data.get('acknowledgments',{}):
                        require(current not in seen_chain,'Circular receipt resolution')
                        seen_chain.add(current)
                        event=data['acknowledgments'][current]
                        require(isinstance(event,dict),'Invalid resolution acknowledgment')
                        if event.get('event')!='superseded':break
                        current=event.get('replacement_id')
            impacts = [j for j in meta['judgments'] if j['disposition'] != 'retain']
            visible = acknowledged != 'superseded' and (binding != 'current' or (bool(impacts) and acknowledged not in {'completed','rejected'}))
            items.append({'receipt_id':record['id'],'recorded_stage':record['status'],
                'coverage':meta['coverage'],'source':deepcopy(record['source']),
                'targets':deepcopy(record['targets']),'spans':deepcopy(meta['spans']),
                'judgments':[{k:v for k,v in j.items() if k != 'next_action' or
                              (binding == 'current' and acknowledged not in {'completed','rejected','superseded'})}
                             for j in meta['judgments']], 'binding':binding,'error':problem,
                'acknowledgment':acknowledged,'needs_review':visible,
                'reminder_due':visible and (binding != 'current' or acknowledged != 'shown'),
                'formal_state_changed':False})
        except READ_ERRORS as exc:
            errors.append(record['id'] + ': ' + str(exc))
    return {'items':items,'errors':errors,'legacy_without_continuity':legacy,'state_sha256':version}


def context_notice(root: Path) -> tuple[str, dict]:
    view = collect(root)
    pending = [item for item in view['items'] if item['needs_review']]
    if not pending and not view['errors']:
        return '', view
    identifiers = sorted({j['id'] for item in pending for j in item['judgments']
                          if re.fullmatch(r'D-\d+', str(j.get('id','')))})
    shown = ', '.join(identifiers[:3]) or 'source scope'
    notice = ('## Source Review\n\n'
        f'- Review required: {len(pending)} receipt(s); judgments: {shown}; errors: {len(view["errors"])}.\n'
        '- Expand: `flg source pending`; inspect changed evidence before relying on linked judgments.\n'
        '- Source changes require review. Formal decision status remains under the normal review path.\n\n')
    return notice, view


def trace(root: Path, path: str, receipt_id: str | None = None, limit: int = 12) -> dict:
    relative(path)
    require(type(limit) is int and 1 <= limit <= 100, 'Trace limit must be 1..100')
    try:
        actual = digest(read_bytes(root, path))
    except FileNotFoundError:
        actual = None
    data, version = load(root)
    matches = []
    for record in data['receipts']:
        if receipt_id is not None and record['id'] != receipt_id:
            continue
        source = record.get('source', {})
        require(isinstance(source,dict) and isinstance(record.get('targets', []),list), 'Invalid receipt references')
        parents = source.get('derived_from', [])
        require(isinstance(parents,list) and all(isinstance(p,dict) for p in parents), 'Invalid parent references')
        refs = [('source',source), *[('target',t) for t in record.get('targets',[])], *[('parent',p) for p in parents]]
        roles = [{'role':role,'version_binding':'unknown' if not ref.get('sha256') or actual is None else
                  'current' if ref['sha256']==actual else 'stale'}
                 for role,ref in refs if isinstance(ref,dict) and ref.get('path')==path]
        if roles:
            meta = record.get('continuity', {})
            require(isinstance(meta,dict), 'Invalid continuity metadata')
            parent_bindings = []
            for parent in parents:
                try:
                    current = digest(read_bytes(root,parent.get('path')))
                except FileNotFoundError:
                    current = None
                parent_bindings.append({'path':parent['path'],'version_binding':
                    'unknown' if current is None or not parent.get('sha256') else
                    'current' if current == parent['sha256'] else 'stale'})
            matches.append({'receipt_id':record['id'],'recorded_stage':record.get('status'),
                'source_path':source.get('path'),'matches':roles,
                'coverage':meta.get('coverage','unknown'),
                'judgments':[j.get('id') for j in meta.get('judgments',[]) if isinstance(j,dict)],
                'locators':[{'start':s.get('start'),'end':s.get('end')} for s in meta.get('spans',[]) if isinstance(s,dict)],
                'parents':parent_bindings,'formal_state_changed':False})
    from .source_inventory import describe
    return {'source':{'path':path,'sha256':actual,'status':'present' if actual else 'unknown',
                     'discovery':describe(root,path) if actual else None},
            'items':matches[:limit],'total':len(matches),'omitted':max(0,len(matches)-limit),
            'receipt_filter':receipt_id,'state_sha256':version,
            'notice':'Byte bindings and host declarations only; semantic absorption and authority are not verified. Use --receipt for an exact reverse lookup.'}
