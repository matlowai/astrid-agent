"""Editorial analysis consumes artifacts without scheduling video pack actions."""
import json
import sys
from pathlib import Path

import pytest
import yaml

from astrid.packs.editorial.actions.editor_review import run as review
from astrid.packs.editorial.actions.refine import run as refine
from astrid.packs.editorial.actions.validate import run as validate
from astrid.packs.video_editing.actions.hype.config import STEP_ORDER


def test_graph_does_not_schedule_video_cut_and_hype_order_is_preserved():
    manifest = yaml.safe_load((Path(__file__).resolve().parents[3] / "astrid/packs/editorial/pack.yaml").read_text())
    for name in ("refine", "editor_review", "validate"):
        assert "video_editing.cut" not in manifest["actions"][name]["graph"]["depends_on"]
    assert [step for step in STEP_ORDER if step in {"cut", "refine", "render", "editor_review", "validate"}] == [
        "cut", "refine", "render", "editor_review", "validate"
    ]


def test_editor_review_refuses_missing_render(tmp_path):
    with pytest.raises(FileNotFoundError, match="rendered video not found"):
        review.main(["--brief-dir", str(tmp_path), "--run-dir", str(tmp_path), "--out", str(tmp_path)])


def test_refine_refuses_missing_materialized_assets(tmp_path):
    args = [item for name in ("arrangement", "pool", "timeline", "assets", "metadata", "transcript")
            for item in (f"--{name}", str(tmp_path / f"{name}.json"))]
    with pytest.raises((FileNotFoundError, ValueError)):
        refine.main([*args, "--out", str(tmp_path), "--skip-whisper"])


def test_validate_requires_and_accepts_supplied_files(tmp_path, monkeypatch):
    video, timeline, metadata = (tmp_path / name for name in ("clip.mp4", "timeline.json", "metadata.json"))
    monkeypatch.setattr(sys, "argv", ["validate", "--video", str(video), "--timeline", str(timeline), "--metadata", str(metadata)])
    with pytest.raises(SystemExit, match="video not found"):
        validate.main()
    video.write_bytes(b"video")
    with pytest.raises(SystemExit, match="required file not found"):
        validate.main()
    timeline.write_text(json.dumps({"theme": "banodoco-default", "tracks": [{"id": "v1", "kind": "visual", "label": "Speaker"}], "clips": [{"id": "clip_g_1", "at": 0, "track": "v1", "clipType": "text-card", "hold": 4}]}))
    metadata.write_text(json.dumps({"clips": {}}))
    assert validate.main() == 0
    assert json.loads((tmp_path / "validation.json").read_text())["summary"]["skipped_no_audio"]
