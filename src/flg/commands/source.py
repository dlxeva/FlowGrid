"""Portable source inventory and explicit processing receipt commands."""
from pathlib import Path
from typing import Optional
import json

import typer

from ..core import source_receipts as receipts

app = typer.Typer(help='Discover sources and track reviewed scope and judgment impact', no_args_is_help=True)


def _run(action):
    try:
        result = action()
    except (ValueError, OSError, UnicodeError, KeyError, TypeError, RuntimeError) as exc:
        typer.echo(json.dumps({'error':str(exc)},ensure_ascii=False))
        raise typer.Exit(2)
    typer.echo(json.dumps(result,ensure_ascii=False,indent=2))
    return result


@app.command('inventory')
def inventory(config: Optional[str] = typer.Option(None,'--config',help='Exact project-relative source-root configuration')):
    from ..core.source_inventory import inventory as scan
    root = Path.cwd()
    _run(lambda:scan(root,receipts.parse_json(receipts.read_bytes(root,config)) if config else None))


@app.command('prepare')
def prepare(input: str = typer.Option(...,'--input'), output: str = typer.Option(...,'--output')):
    root = Path.cwd()
    def action():
        from ..core.source_io import create_candidate
        candidate = receipts.prepare(root,receipts.parse_json(receipts.read_bytes(root,input)))
        text = json.dumps(candidate,ensure_ascii=False,indent=2)+'\n'
        create_candidate(root,output,text)
        return {'candidate':output,'applied':False,'sha256':receipts.digest(text)}
    _run(action)


@app.command('record')
def record(input: str = typer.Option(...,'--input'), expected_sha256: str = typer.Option(...,'--expected-sha256')):
    root = Path.cwd()
    result = _run(lambda:receipts.register(root,receipts.parse_json(receipts.read_bytes(root,input)),expected_sha256))
    if result['validation'] != 'current':
        raise typer.Exit(1)


@app.command('pending')
def pending(judgment: Optional[str] = typer.Option(None,'--judgment'), reminders: bool = typer.Option(False,'--reminders'),
            limit: int = typer.Option(12,'--limit',min=1,max=100)):
    def action():
        result = receipts.collect(Path.cwd(),judgment)
        selected = [item for item in result['items'] if item['reminder_due']] if reminders else [
            item for item in result['items'] if item['needs_review']]
        result.update(total=len(selected),omitted=max(0,len(selected)-limit))
        result['items'] = [{'receipt_id':item['receipt_id'],'source_path':item['source']['path'],
            'recorded_stage':item['recorded_stage'],'coverage':item['coverage'],
            'binding':item['binding'],'judgments':[j['id'] for j in item['judgments']],
            'acknowledgment':item['acknowledgment'],'reminder_due':item['reminder_due'],
            'error':item['error'],'formal_state_changed':False} for item in selected[:limit]]
        result['expand'] = 'flg source show RECEIPT_ID'
        return result
    view = _run(action)
    # Machine-readable raw view keeps closed historical records distinguishable.
    # reminder_due is provided per record; reads never acknowledge a display.
    if view['errors']:
        raise typer.Exit(1)


@app.command('show')
def show(receipt_id: str):
    def action():
        view = receipts.collect(Path.cwd())
        item = next((item for item in view['items'] if item['receipt_id']==receipt_id),None)
        receipts.require(item is not None, 'Unknown or invalid continuity receipt; use source trace for legacy references')
        return {'item':item,'errors':view['errors'],'state_sha256':view['state_sha256']}
    _run(action)


@app.command('acknowledge')
def acknowledge(receipt_id: str, outcome: str = typer.Option(...,'--outcome'),
                reason: str = typer.Option(...,'--reason'), expected_sha256: str = typer.Option(...,'--expected-sha256')):
    _run(lambda:receipts.acknowledge(Path.cwd(),receipt_id,outcome,expected_sha256,reason))


@app.command('trace')
def trace(path: str, receipt: Optional[str] = typer.Option(None,'--receipt'), limit: int = typer.Option(12,'--limit')):
    _run(lambda:receipts.trace(Path.cwd(),path,receipt,limit))


@app.command('resolve')
def resolve(receipt_id: str, replacement: str = typer.Option(...,'--replacement'),
            reason: str = typer.Option(...,'--reason'), expected_sha256: str = typer.Option(...,'--expected-sha256')):
    _run(lambda:receipts.resolve(Path.cwd(),receipt_id,replacement,expected_sha256,reason))
