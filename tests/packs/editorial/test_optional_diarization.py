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
