"""Scratchpad of render presets.

Each module here is ONE render and exposes ``build(settings: dict) -> str``
returning a self-contained Blender Python script. The script may use the
placeholders ``__MESH_FILE__`` and ``__OUTPUT__`` (filled by the render runner
with the resolved mesh path and output directory). Adding a render requires registering its module in this package. See ``README.md``.

This package is intentionally OUTSIDE the core engine (``render_core.py``):
core = reusable machinery; ``renders/`` = specific, creative, disposable scenes.
"""

from __future__ import annotations

from typing import Any, Callable

from astrid.packs.blender.renders.wink_turn import build as build_wink_turn

# Register each shipped preset explicitly; new presets add an entry here.
PRESETS: dict[str, Callable[[dict[str, Any] | None], str]] = {
    "wink_turn": build_wink_turn,
}


def get_builder(name: str) -> Callable[[dict[str, Any] | None], str]:
    if name not in PRESETS:
        raise KeyError(
            f"unknown render preset {name!r}; available: {sorted(PRESETS)}"
        )
    return PRESETS[name]


def list_presets() -> list[str]:
    return sorted(PRESETS)
