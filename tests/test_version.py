"""Package, source and CLI versions agree without rewriting project history."""
import json
from importlib.metadata import version
from pathlib import Path
import re

from typer.testing import CliRunner
from flg import __version__
from flg.cli import app


def test_package_and_source_version_agree():
    root = Path(__file__).resolve().parents[1]
    declared = re.search(r'^version = "([^"]+)"', (root/'pyproject.toml').read_text(), re.M)[1]
    assert declared == __version__ == version('flowgrid')


def test_cli_version_matches_import():
    result = CliRunner().invoke(app, ['version'])
    assert result.exit_code == 0 and f'FlowGrid v{__version__}' in result.output


def test_status_separates_runtime_and_project_version(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ['init', 'Version boundary']).exit_code == 0
    path = tmp_path/'.flg/state.json'
    state = json.loads(path.read_text())
    state['flg_version'] = '0.3.0'
    path.write_text(json.dumps(state))
    before = path.read_bytes()
    result = runner.invoke(app, ['status'])
    assert result.exit_code == 0
    assert f'Runtime version: {__version__}' in result.output
    assert 'Project recorded version: 0.3.0' in result.output
    assert path.read_bytes() == before
