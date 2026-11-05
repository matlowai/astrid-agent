"""Editorial-owned built-in pipeline steps and brief preparation."""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from astrid.pack_api import executor_argv, sha256_file

@dataclass(frozen=True)
class Step:
    name: str
    sentinels: tuple[str, ...]
    build_cmd: Callable[[argparse.Namespace], list[str]]
    per_brief: bool = False
    always_run: bool = False
    invoke: Callable[[argparse.Namespace], Path] | None = None
    # Sequence-local policy for actions whose public graph is independent of Hype.
    action_id: str | None = None
    pipeline_requirements: tuple[str, ...] = ()
    pipeline_provides: tuple[str, ...] = ()

def step_argv(action_id: str, python_exec: str) -> list[str]:
    """Argv tokens for invoking a qualified public child action."""
    return executor_argv(action_id, python_exec)

def add_extra_args(args: argparse.Namespace, step_name: str, cmd: list[str]) -> list[str]:
    return cmd + args.extra_args.get(step_name, [])

def probe_audio_duration(path: Path | str) -> float:
    from astrid.pack_api import ffprobe_duration_seconds

    return ffprobe_duration_seconds(path)

def _arrange_target_duration(args: argparse.Namespace) -> float | None:
    if args.video is not None:
        return None
    if args.audio is not None:
        return probe_audio_duration(args.audio)
    return float(args.target_duration)

STEP_ORDER = ('transcribe', 'scenes', 'quality_zones', 'shots', 'triage', 'quote_scout', 'arrange', 'refine', 'editor_review', 'validate')

def build_pool_steps() -> list[Step]:
    return [
        Step(
                    "transcribe",
                    ("transcript.json",),
                    lambda args: add_extra_args(
                        args,
                        "transcribe",
                        [
                            *step_argv("editorial.transcribe", args.python_exec),
                            "--audio",
                            str(args.audio),
                            "--out",
                            str(args.out),
                            *(["--env-file", str(args.env_file)] if args.env_file else []),
                        ],
                    ),
                ),
        Step(
                    "scenes",
                    ("scenes.json",),
                    lambda args: add_extra_args(
                        args,
                        "scenes",
                        [*step_argv("editorial.scenes", args.python_exec), "--video", str(args.video), "--out", str(args.out / "scenes.json")],
                    ),
                ),
        Step(
                    "quality_zones",
                    ("quality_zones.json",),
                    lambda args: add_extra_args(
                        args,
                        "quality_zones",
                        [
                            *step_argv("editorial.quality_zones", args.python_exec),
                            str(args.video),
                            "--out",
                            str(args.out / "quality_zones.json"),
                        ],
                    ),
                ),
        Step(
                    "shots",
                    ("shots.json",),
                    lambda args: add_extra_args(
                        args,
                        "shots",
                        [*step_argv("editorial.shots", args.python_exec), "--video", str(args.video), "--scenes", str(args.out / "scenes.json"), "--out", str(args.out)],
                    ),
                ),
        Step(
                    "triage",
                    ("scene_triage.json",),
                    lambda args: add_extra_args(
                        args,
                        "triage",
                        [
                            *step_argv("editorial.triage", args.python_exec),
                            "--scenes",
                            str(args.out / "scenes.json"),
                            "--shots",
                            str(args.out / "shots.json"),
                            "--shots-dir",
                            str(args.out),
                            "--out",
                            str(args.out),
                            *(["--env-file", str(args.env_file)] if args.env_file else []),
                        ],
                    ),
                ),
        Step(
                    "quote_scout",
                    ("quote_candidates.json",),
                    lambda args: add_extra_args(
                        args,
                        "quote_scout",
                        [
                            *step_argv("editorial.quote_scout", args.python_exec),
                            "--transcript",
                            str(args.out / "transcript.json"),
                            "--out",
                            str(args.out),
                            *(["--env-file", str(args.env_file)] if args.env_file else []),
                        ],
                    ),
                ),
        Step(
                    "arrange",
                    ("arrangement.json",),
                    lambda args: add_extra_args(
                        args,
                        "arrange",
                        [
                            *step_argv("editorial.arrange", args.python_exec),
                            "--pool",
                            str(args.out / "pool.json"),
                            "--brief",
                            str(args.brief_copy),
                            "--out",
                            str(args.brief_out),
                            "--source-slug",
                            args.source_slug,
                            "--brief-slug",
                            args.brief_slug,
                            # extends prior plan Step 14
                            *(["--theme", str(args.theme)] if getattr(args, "theme_explicit", False) and getattr(args, "theme", None) else []),
                            *(
                                ["--target-duration", f"{target_duration:.6f}"]
                                if (target_duration := _arrange_target_duration(args)) is not None
                                else []
                            ),
                            *(["--allow-generative-effects"] if (args.video is None or getattr(args, "allow_generative_effects", False) or getattr(args, "brief_allow_generative_visuals", False)) else []),
                            *(["--no-audio"] if args.video is None and args.audio is None else []),
                            *(["--env-file", str(args.env_file)] if args.env_file else []),
                        ],
                    ),
                    per_brief=True,
                ),
        Step(
                    "refine",
                    ("refine.json",),
                    lambda args: add_extra_args(
                        args,
                        "refine",
                        [
                            *step_argv("editorial.refine", args.python_exec),
                            "--arrangement",
                            str(args.brief_out / "arrangement.json"),
                            "--pool",
                            str(args.out / "pool.json"),
                            "--timeline",
                            str(args.brief_out / "hype.timeline.json"),
                            "--assets",
                            str(args.brief_out / "hype.assets.json"),
                            "--metadata",
                            str(args.brief_out / "hype.metadata.json"),
                            "--transcript",
                            str(args.out / "transcript.json"),
                            "--out",
                            str(args.brief_out),
                            *(["--primary-asset", args.primary_asset] if getattr(args, "primary_asset", None) else []),
                            *(["--env-file", str(args.env_file)] if args.env_file else []),
                        ],
                    ),
                    per_brief=True,
                ),
        Step(
                    "editor_review",
                    ("editor_review.json",),
                    lambda args: add_extra_args(
                        args,
                        "editor_review",
                        [
                            *step_argv("editorial.editor_review", args.python_exec),
                            "--brief-dir",
                            str(args.brief_out),
                            "--run-dir",
                            str(args.out),
                            "--out",
                            str(args.brief_out),
                            "--iteration",
                            str(getattr(args, "editor_iteration", 1)),
                            *(["--env-file", str(args.env_file)] if args.env_file else []),
                        ],
                    ),
                    per_brief=True,
                ),
        Step(
                    "validate",
                    ("validation.json",),
                    lambda args: add_extra_args(
                        args,
                        "validate",
                        [
                            *step_argv("editorial.validate", args.python_exec),
                            "--video",
                            str(args.brief_out / "hype.mp4"),
                            "--timeline",
                            str(args.brief_out / "hype.timeline.json"),
                            "--metadata",
                            str(args.brief_out / "hype.metadata.json"),
                            "--out",
                            str(args.brief_out / "validation.json"),
                            *(["--env-file", str(args.env_file)] if args.env_file else []),
                        ],
                    ),
                    per_brief=True,
                ),
    ]

def _coerce_frontmatter_value(raw: str) -> object:
    """Coerce a YAML-like scalar string into a Python value.

    Recognizes: ``true``/``false`` (case-insensitive) -> bool; bare integers and
    floats -> numeric; strings wrapped in matching single or double quotes ->
    unquoted str; everything else -> raw str (whitespace-trimmed).
    """
    text = raw.strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if (text.startswith("\"") and text.endswith("\"") and len(text) >= 2) or (
        text.startswith("'") and text.endswith("'") and len(text) >= 2
    ):
        return text[1:-1]
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text

def parse_brief_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """Split an optional YAML-like ``---``-fenced frontmatter block off a brief.

    The frontmatter must begin on line 1 with a line containing only ``---``,
    end with another line containing only ``---``, and contain
    ``key: value`` pairs (one per line). Blank lines and ``#`` comment lines
    inside the block are tolerated. When no frontmatter is present, returns
    ``({}, text)`` unchanged.
    """
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return {}, text
    metadata: dict[str, object] = {}
    closing_index: int | None = None
    for index in range(1, len(lines)):
        line = lines[index]
        stripped = line.strip()
        if stripped == "---":
            closing_index = index
            break
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            # Malformed line inside frontmatter; treat the file as having no
            # frontmatter to avoid silently corrupting a brief that happens to
            # start with three dashes (e.g. an em-dash separator).
            return {}, text
        key, _, value = stripped.partition(":")
        key = key.strip()
        if not key:
            return {}, text
        metadata[key] = _coerce_frontmatter_value(value)
    if closing_index is None:
        return {}, text
    body = "\n".join(lines[closing_index + 1 :])
    return metadata, body

def _brief_allow_generative_visuals(metadata: dict[str, object]) -> bool:
    """Return the truth value of the ``allow_generative_visuals`` frontmatter key.

    Treats missing keys, non-bool values, and the literal ``False`` as
    ``False`` so a malformed brief never silently enables generative effects.
    """
    return metadata.get("allow_generative_visuals") is True

def prepare_brief_artifacts(args: argparse.Namespace) -> None:
    """Stage the brief and invalidate generated per-brief outputs on changes."""
    args.brief_out.mkdir(parents=True, exist_ok=True)
    metadata, body = parse_brief_frontmatter(args.brief.read_text(encoding="utf-8"))
    args.brief_frontmatter = metadata
    args.brief_allow_generative_visuals = _brief_allow_generative_visuals(metadata)
    body_bytes = body.encode("utf-8")
    existing_hash = sha256_file(args.brief_copy) if args.brief_copy.is_file() else None
    if existing_hash == hashlib.sha256(body_bytes).hexdigest():
        return
    if existing_hash is not None:
        # Match the Hype workflow's generated per-brief artifact contract.
        for name in (
            "arrangement.json", "hype.timeline.json", "hype.assets.json",
            "hype.metadata.json", "refine.json", "hype.mp4",
            "hype.mp4.provenance.json", "editor_review.json", "validation.json",
        ):
            (args.brief_out / name).unlink(missing_ok=True)
    args.brief_copy.write_bytes(body_bytes)
