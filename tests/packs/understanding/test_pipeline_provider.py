import argparse
import sys

from astrid.core.execution.executor.runner import ExecutorRunRequest, _run_builtin_executor
from astrid.core.execution.executor.schema import ExecutorDefinition
from astrid.packs.understanding import pipeline
from astrid.packs.video_editing.actions.hype.steps import build_pool_steps as hype_steps


def test_command_matches_retained_provider(tmp_path):
    args = argparse.Namespace(out=tmp_path, video=tmp_path / 'video', python_exec=sys.executable,
                              env_file=tmp_path / 'env', extra_args={'scene_describe': ['--extra']})
    old = next(s for s in hype_steps() if s.name == 'scene_describe')
    step = pipeline.build_pool_steps()[0]
    assert step.build_cmd(args) == old.build_cmd(args)
    assert step.sentinels == old.sentinels


def test_non_dry_dispatch_preserves_brief(tmp_path, monkeypatch):
    brief = tmp_path / 'brief.txt'
    brief.write_text('original')
    marker = tmp_path / 'marker'
    monkeypatch.setattr(pipeline, 'executor_argv', lambda *_: [sys.executable, '-c',
        "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('ran')", str(marker)])
    executor = ExecutorDefinition(id='understanding.scene_describe', name='Scene describe', kind='built_in', version='1',
        metadata={'command_builder': 'astrid.packs.understanding.pipeline.build_pool_steps', 'pipeline_step': 'scene_describe'})
    result = _run_builtin_executor(executor, ExecutorRunRequest(executor_id=executor.id, out=tmp_path, brief=brief))
    assert result.returncode == 0
    assert marker.read_text() == 'ran'
    assert brief.read_text() == 'original'
