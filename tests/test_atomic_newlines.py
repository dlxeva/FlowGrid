"""Atomic text writes preserve declared UTF-8 bytes on every platform."""
from hashlib import sha256
import os

import pytest
import yaml

from flg.core.operations import atomic_write_text
from flg.core.capture_followup import collect, record


@pytest.mark.parametrize('text', ['one\ntwo\n', 'one\r\ntwo\r\n', 'one\r\ntwo\n'])
def test_atomic_writer_has_no_platform_newline_translation(tmp_path, monkeypatch, text):
    original = os.fdopen
    def windows_default(fd, *args, **kwargs):
        if 'b' not in (args[0] if args else kwargs.get('mode', 'r')):
            kwargs.setdefault('newline', '\r\n')
        return original(fd, *args, **kwargs)
    monkeypatch.setattr(os, 'fdopen', windows_default)
    path = tmp_path/'text.md'
    atomic_write_text(path, text)
    assert path.read_bytes() == text.encode('utf-8')


def test_crlf_capture_body_hash_and_retry_survive_atomic_record(tmp_path, monkeypatch):
    original = os.fdopen
    def windows_default(fd, *args, **kwargs):
        if 'b' not in (args[0] if args else kwargs.get('mode', 'r')):
            kwargs.setdefault('newline', '\r\n')
        return original(fd, *args, **kwargs)
    monkeypatch.setattr(os, 'fdopen', windows_default)
    folder = tmp_path/'.flg/captures'
    folder.mkdir(parents=True)
    path = folder/'cap-crlf.md'
    raw = b'---\r\nid: cap-crlf\r\nstatus: pending_review\r\nclaim: Wait for evidence\r\n---\r\n\r\n# Original body\r\nKeep exactly.\r\n'
    path.write_bytes(raw)
    before = sha256(raw).hexdigest()
    data = {'disposition': 'awaiting_evidence', 'reason': 'Reviewed, still waiting',
            'waiting_for': ['Pilot evidence'], 'review_trigger': 'Evidence arrives'}
    result = record(tmp_path, path.stem, data, before)
    updated = path.read_bytes()
    assert result['sha256'] == sha256(updated).hexdigest()
    assert updated.endswith(b'\r\n# Original body\r\nKeep exactly.\r\n')
    assert b'\r\r\n' not in updated
    assert collect(tmp_path)['counts']['awaiting_evidence'] == 1
    assert record(tmp_path, path.stem, data, before)['idempotent']
    assert path.read_bytes() == updated
    meta = yaml.safe_load(updated.decode().split('---', 2)[1])
    assert meta['status'] == 'pending_review'
