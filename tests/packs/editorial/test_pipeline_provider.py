from __future__ import annotations

import sys

from astrid.core.execution.executor.runner import ExecutorRunRequest, _run_builtin_executor, build_pipeline_context
from astrid.core.execution.executor.schema import ExecutorDefinition
from astrid.packs.editorial import pipeline
from astrid.packs.video_editing.actions.hype.steps import build_pool_steps as hype_steps


def test_editorial_commands_match_retained_provider(tmp_path):
    (tmp_path / "source.mp4").write_bytes(b"media")
    request = ExecutorRunRequest(executor_id="editorial.arrange", out=tmp_path,
                                 inputs={"video": str(tmp_path / "source.mp4"), "extra_args": {"arrange": ["--extra"]}})
    args = build_pipeline_context(request)
    args.brief_allow_generative_visuals = True
    old = {step.name: step for step in hype_steps()}
    for step in pipeline.build_pool_steps():
        original = old[step.name]
        assert step.build_cmd(args) == original.build_cmd(args)
        assert (step.sentinels, step.per_brief, step.always_run) == (original.sentinels, original.per_brief, original.always_run)


def test_brief_preparation_preserves_unrelated_and_unchanged_outputs(tmp_path):
    brief = tmp_path / "source.txt"
    brief.write_text("---\nallow_generative_visuals: true\n---\nfirst")
    args = build_pipeline_context(ExecutorRunRequest(executor_id="editorial.arrange", out=tmp_path, brief=brief))
    pipeline.prepare_brief_artifacts(args)
    assert args.brief_copy.read_text() == "first"
    assert args.brief_allow_generative_visuals is True
    generated_names = (
        "arrangement.json", "hype.timeline.json", "hype.assets.json",
        "hype.metadata.json", "refine.json", "hype.mp4",
        "hype.mp4.provenance.json", "editor_review.json", "validation.json",
    )
    generated = [args.brief_out / name for name in generated_names]
    for path in generated:
        path.write_text("generated")
    unrelated = args.brief_out / "personal-notes.txt"
    unrelated.write_text("keep")
    other_brief = tmp_path / "other-brief"
    other_brief.mkdir()
    (other_brief / "hype.mp4").write_text("other")
    pipeline.prepare_brief_artifacts(args)
    assert all(path.read_text() == "generated" for path in generated)
    brief.write_text("second")
    pipeline.prepare_brief_artifacts(args)
    assert all(not path.exists() for path in generated)
    assert unrelated.read_text() == "keep"
    assert (other_brief / "hype.mp4").read_text() == "other"
    assert args.brief_copy.read_text() == "second"


def test_real_builtin_dispatch_uses_editorial_provider(tmp_path, monkeypatch):
    brief = tmp_path / "brief.txt"
    brief.write_text("brief")
    marker = tmp_path / "marker"
    monkeypatch.setattr(pipeline, "executor_argv", lambda *_: [
        sys.executable, "-c", "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('ran')", str(marker)
    ])
    executor = ExecutorDefinition(id="editorial.scenes", name="Scenes", kind="built_in", version="1",
        metadata={"command_builder": "astrid.packs.editorial.pipeline.build_pool_steps", "pipeline_step": "scenes"})
    result = _run_builtin_executor(executor, ExecutorRunRequest(executor_id=executor.id, out=tmp_path, brief=brief))
    assert result.returncode == 0
    assert marker.read_text() == "ran"
    assert brief.read_text() == "brief"
