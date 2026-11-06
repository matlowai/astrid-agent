import builtins
import importlib

import pytest


def test_diarization_is_optional_and_missing_dependency_refuses_before_work(monkeypatch, tmp_path):
    monkeypatch.setenv("ASTRID_INTERNAL_INVOCATION", "1")
    transcribe = importlib.import_module("astrid.packs.editorial.actions.transcribe.run")
    original_import = builtins.__import__

    def missing_pyannote(name, *args, **kwargs):
        if name == "pyannote.audio":
            raise ModuleNotFoundError("No module named 'pyannote'", name="pyannote")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_pyannote)
    monkeypatch.setattr(transcribe, "require_hf_token", lambda mode: pytest.fail("unexpected credential lookup"))
    monkeypatch.setattr(transcribe, "run", lambda *args, **kwargs: pytest.fail("unexpected ffmpeg"))
    assert transcribe.diarize_audio(tmp_path / "audio.wav", tmp_path, None) is None
    with pytest.raises(SystemExit, match="optional pyannote.audio dependency"):
        transcribe.diarize_audio(tmp_path / "audio.wav", tmp_path, "pyannote")


@pytest.mark.parametrize("version,valid", [(None, False), ("3.0.1", False), ("4.0.0", False), ("3.1.1", True)])
def test_requested_mode_qualifies_selected_interpreter_before_effects(monkeypatch, version, valid):
    monkeypatch.setenv("ASTRID_INTERNAL_INVOCATION", "1")
    transcribe = importlib.import_module("astrid.packs.editorial.actions.transcribe.run")
    def installed(name):
        assert name == "pyannote-audio"
        if version is None:
            raise transcribe.metadata.PackageNotFoundError(name)
        return version
    monkeypatch.setattr(transcribe.metadata, "version", installed)
    monkeypatch.setattr(transcribe, "require_runtime_materialized_file", lambda *a, **k: pytest.fail("preflight passed"))
    if valid:
        with pytest.raises(pytest.fail.Exception, match="preflight passed"):
            transcribe.main(["--audio", "unused.wav", "--diarize", "pyannote"])
    else:
        with pytest.raises(SystemExit, match="pyannote-audio>=3.1,<4"):
            transcribe.main(["--audio", "unused.wav", "--diarize", "pyannote"])


def test_base_mode_does_not_query_optional_distribution(monkeypatch):
    monkeypatch.setenv("ASTRID_INTERNAL_INVOCATION", "1")
    transcribe = importlib.import_module("astrid.packs.editorial.actions.transcribe.run")
    monkeypatch.setattr(transcribe.metadata, "version", lambda *_: pytest.fail("optional lookup"))
    transcribe.qualify_diarization(None)
