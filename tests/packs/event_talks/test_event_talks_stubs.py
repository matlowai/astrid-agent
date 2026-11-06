"""Smoke tests: event_talks stubs and data loading."""

import argparse

import pytest

from astrid.packs.video_editing.actions.event_talks.run import (
    ADOS_SUNDAY_SPEAKERS,
    _exec_render_manifest,
)


def test_ados_sunday_speakers_loads():
    assert isinstance(ADOS_SUNDAY_SPEAKERS, list)
    assert len(ADOS_SUNDAY_SPEAKERS) > 0
    first = ADOS_SUNDAY_SPEAKERS[0]
    assert "speaker" in first
    assert "title" in first


def test_render_manifest_raises():
    args = argparse.Namespace()
    with pytest.raises(NotImplementedError, match="event_talks.render_manifest"):
        _exec_render_manifest(args)


def test_live_plan_template_uses_local_steps_and_output_placeholders(tmp_path):
    from astrid.packs.video_editing.actions.event_talks.plan_template import build_plan_v2

    plan = build_plan_v2(python_exec="python3", run_root=tmp_path, run_id="test")
    steps = {step["id"]: step for step in plan["steps"]}
    assert set(steps) == {"ados-sunday-template", "search-transcript", "find-holding-screens", "render"}
    assert all(step["adapter"] == "local" for step in steps.values())
    assert all("{produces_root}" in step["command"] for step in steps.values())
    assert "ados-sunday-template/v1/produces/ados-sunday-template.json" in steps["render"]["command"]
