"""Explicit host interface for opt-in, local task continuation records."""
from pathlib import Path

import json
import typer

from ..core import task_continuity as tasks
from ..core.source_receipts import parse_json, read_bytes

app = typer.Typer(help="Opt-in local task continuation (host-asserted actors)", no_args_is_help=True)


def _run(action):
    try:
        result = action()
    except (ValueError, OSError, UnicodeError, KeyError, TypeError, RuntimeError) as exc:
        typer.echo(json.dumps({"error": str(exc)}, ensure_ascii=False))
        raise typer.Exit(2)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


def _configure(input: str, enabled: bool):
    root = Path.cwd()
    def action():
        payload = parse_json(read_bytes(root, input))
        if "enabled" in payload and payload["enabled"] is not enabled:
            raise ValueError("Input enabled flag conflicts with command")
        return tasks.configure(root, {**payload, "enabled": enabled})
    _run(action)


@app.command("enable")
def enable(input: str = typer.Option(..., "--input", help="Project-relative host authorization JSON")):
    """Explicitly enable this extension for one project; never imports history."""
    _configure(input, True)


@app.command("disable")
def disable(input: str = typer.Option(..., "--input")):
    """Disable only after live work is resolved, preserving task history."""
    _configure(input, False)


@app.command("list")
def list_tasks():
    """Read bounded task state without acquiring execution ownership."""
    _run(lambda: tasks.collect(Path.cwd()))


@app.command("show")
def show(task_id: str = typer.Argument(...)):
    """Read one task, including source drift and continuation checks."""
    _run(lambda: tasks.show(Path.cwd(), task_id))


@app.command("apply")
def apply(task_id: str = typer.Argument(...), input: str = typer.Option(..., "--input")):
    """Apply one explicit, revision-checked operation; no external tool execution."""
    root = Path.cwd()
    _run(lambda: tasks.apply(root, task_id, parse_json(read_bytes(root, input))))
