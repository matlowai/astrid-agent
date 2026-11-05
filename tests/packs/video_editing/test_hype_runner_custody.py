from __future__ import annotations

import argparse
import io
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from astrid.core.execution import pipeline_step as runner
from astrid.packs.video_editing.actions.hype.steps import Step


def _callback(args):
    return args.out


def test_hype_resources_and_shared_callback_worker(tmp_path):
    pack_root = Path(__file__).resolve().parents[3] / "astrid/packs/video_editing"
    manifest = yaml.safe_load((pack_root / "pack.yaml").read_text())
    hype = manifest["actions"]["hype"]
    for resource in hype["resources"]:
        assert (pack_root / resource["path"]).is_file()

    step = Step("fixture", (), lambda _: [], invoke=print)
    args = argparse.Namespace(out=tmp_path, verbose=False)
    assert runner.run_step(step, [], args) == 0
    assert "Namespace(" in (tmp_path / "logs/fixture.log").read_text()


@pytest.mark.parametrize("inherited", [True, False])
@pytest.mark.parametrize("callback", [True, False])
def test_hype_launch_registers_its_own_custody_and_preserves_session(tmp_path, monkeypatch, inherited, callback):
    if inherited:
        monkeypatch.setenv("ASTRID_INTERNAL_INVOCATION", "1")
    else:
        monkeypatch.delenv("ASTRID_INTERNAL_INVOCATION", raising=False)
    calls = []
    process = SimpleNamespace(pid=123, stdout=io.StringIO("ready\n"), poll=lambda: 0, wait=lambda: 0)
    def fresh(argv, **kwargs):
        calls.append(("fresh", kwargs))
        return process
    def own_inherited(argv, **kwargs):
        calls.append(("inherited", kwargs))
        return process
    monkeypatch.setattr(runner, "popen_owned_group", fresh)
    monkeypatch.setattr(runner, "popen_owned_process", own_inherited)
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("bare launch bypass"))
    monkeypatch.setattr(runner, "_terminate_owned_tree", lambda owned: calls.append(("cleanup", owned)))
    monkeypatch.setattr(runner, "_release_owned_group", lambda owned: calls.append(("release", owned)))
    args = argparse.Namespace(out=tmp_path, verbose=False)
    step = Step("fixture", (), lambda _: [], invoke=_callback if callback else None)
    assert runner.run_step(step, ["/selected/tool"], args) == 0
    assert calls[0][0] == ("inherited" if inherited else "fresh")
    assert calls[0][1].get("start_new_session", False) is False
    assert ("cleanup", process) in calls
    assert ("release", process) in calls if not inherited else ("release", process) not in calls
