from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from astrid.sdk.timeline import media_add
from astrid.sdk.timeline._common import TimelineEditError
from tests.timeline.test_media_add_audio import _Session

OLD = {'asset': 'take-1', 'object_id': 'sha256:' + '1' * 64, 'generation_id': 'generation-1', 'variant_id': 'variant-1'}
PIN = {
    'asset': 'take-2',
    'object_id': 'sha256:' + 'ab12cd34' + '0' * 56,
    'generation_id': 'generation-2',
    'variant_id': 'variant-2',
}
VERIFIED = {'media_type': 'video/mp4', 'duration_seconds': 3.0}
C5 = {'id': 'c5', 'clipType': 'media', 'track': 'V1', 'asset': 'take-1', 'at': 4.0,
      'from': 0.5, 'to': 2.5, 'speed': 1, 'label': 'C5 · take 1',
      'generation': {'snap': {'take': 'take-1'}}}
VO = {'id': 'vo-c5', 'clipType': 'media', 'track': 'A2', 'asset': 'line-1', 'at': 4.0, 'from': 0, 'to': 2.0,
      'app': {'astrid': {'segment': 'line-c5', 'words': [[0.2, 0.5, "It's"], [0.5, 0.9, 'you.']]}}}


class _ReplaceSession(_Session):
    def __init__(self):
        super().__init__(tracks=[{'id': 'V1', 'kind': 'visual'}])
        self.bundle['parent']['config']['clips'] = [copy.deepcopy(C5), copy.deepcopy(VO)]
        self.bundle['parent']['config']['registry'] = {'assets': {'take-1': {
            'media_id': OLD['object_id'], 'generationId': 'generation-1', 'variantId': 'variant-1'}}}
        self.state['base'] = {'revision_id': 'rev-1', 'publication_id': 'pub-1'}


@pytest.fixture(autouse=True)
def _capture_without_runtime(monkeypatch):
    monkeypatch.setattr(media_add, '_selection',
                        lambda _session, _bundle, source: (OLD, VERIFIED) if source == 'take-1' else (PIN, VERIFIED))
    monkeypatch.setattr('astrid.sdk.timeline.commands.execute',
                        lambda _bundle, commands, **_kwargs: SimpleNamespace(commands=commands))


def _replace(session, **overrides):
    options = {'expected_head': 'rev-1', 'generation': None, 'idempotency_key': 'retake-c5',
               'dry_run': False, 'via': 'cli', **overrides}
    return media_add.replace_media(session, 'c5', 'new-take.mp4', **options)


def test_the_clip_keeps_its_id_and_a_words_clip_does_not_block_it():
    session = _ReplaceSession()
    result = _replace(session, generation={'snap': {'take': 'take-2'}})

    assert result['data']['replaced'] == {'clip': 'c5', 'old_media': OLD['object_id'], 'new_media': PIN['object_id']}
    swap, patch = session.last_commands
    assert swap['op'] == 'clip.swap-media' and swap['select'] == 'parent/clip:c5'
    assert swap['args'] == {'old_media': OLD, 'media': PIN}
    assert patch['op'] == 'doc.patch' and patch['args']['changes'] == [{
        'op': 'set', 'ref': 'parent', 'path': ['clips', 'id:c5', 'generation'],
        'before': {'state': 'present', 'value': {'snap': {'take': 'take-1'}}}, 'value': {'snap': {'take': 'take-2'}}}]
    assert not any(command['op'] == 'clip.delete' for command in session.last_commands)


def test_without_generation_only_the_media_changes():
    session = _ReplaceSession()
    _replace(session)
    assert [command['op'] for command in session.last_commands] == ['clip.swap-media']


def test_a_stale_head_or_missing_clip_refuses_before_any_import_or_write(monkeypatch):
    session = _ReplaceSession()
    monkeypatch.setattr(media_add, '_selection', lambda *_args: pytest.fail('imported media before refusing'))
    with pytest.raises(TimelineEditError, match='head is rev-1, not rev-0'):
        _replace(session, expected_head='rev-0')
    session.bundle['parent']['config']['clips'] = []
    with pytest.raises(TimelineEditError, match="no parent clip 'c5'"):
        _replace(session)
    assert session.last_commands is None and 'media_input' not in session.state


def test_the_same_key_replays_without_capturing_again(monkeypatch):
    session = _ReplaceSession()
    _replace(session)
    monkeypatch.setattr(media_add, '_selection', lambda *_args: pytest.fail('captured the replay again'))
    assert _replace(session)['status'] == 'already_applied'
