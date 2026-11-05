from pathlib import Path

import pytest

from astrid.packs.blender import renders


def test_registry_covers_shipped_presets_and_refuses_unknown():
    shipped = {p.stem for p in Path(renders.__file__).parent.glob('*.py') if not p.name.startswith('_')}
    assert set(renders.list_presets()) == shipped
    assert callable(renders.get_builder('wink_turn'))
    with pytest.raises(KeyError, match='unknown render preset'):
        renders.get_builder('not_a_preset')
