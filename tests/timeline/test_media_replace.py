from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from astrid.sdk.timeline import media_add
from astrid.sdk.timeline._common import TimelineEditError
from tests.timeline.test_media_add_audio import _Session

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


class _ReplaceSession(_Session):
    def __init__(self):
        super().__init__(tracks=[{'id': 'V1', 'kind': 'visual'}])
        self.bundle['parent']['config']['clips'] = [copy.deepcopy(C5)]
        self.state['base'] = {'revision_id': 'rev-1', 'publication_id': 'pub-1'}


@pytest.fixture(autouse=True)
def _capture_without_runtime(monkeypatch):
    monkeypatch.setattr(media_add, '_selection', lambda _session, _bundle, _source: (PIN, VERIFIED))
    monkeypatch.setattr('astrid.sdk.timeline.commands.execute',
                        lambda _bundle, commands, **_kwargs: SimpleNamespace(commands=commands))


def _replace(session, **overrides):
    options = {'expected_head': 'rev-1', 'generation': None, 'idempotency_key': 'retake-c5',
               'dry_run': False, 'via': 'cli', **overrides}
    return media_add.replace_media(session, 'c5', 'new-take.mp4', **options)


def test_replacement_keeps_the_slot_and_names_both_clips():
    session = _ReplaceSession()
    result = _replace(session, generation={'snap': {'take': 'take-2'}})

    assert result['data']['replaced'] == {'old_clip': 'c5', 'new_clip': 'c5-rab12cd34'}
    assembled, birth, deletion = session.last_commands
    assert assembled['op'] == 'timeline.assembled-target'
    assert deletion == {'schema_version': 1, 'op': 'clip.delete', 'version': '1', 'select': 'parent/clip:c5', 'args': {}}
    row = birth['args']['row']
    assert birth['op'] == 'clip.add-media' and birth['args']['media'] == PIN
    assert row == {**{k: v for k, v in C5.items() if k != 'asset'}, 'id': 'c5-rab12cd34', 'asset': 'take-2',
                   'hold': 2.0, 'generation': {'snap': {'take': 'take-2'}}}


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
