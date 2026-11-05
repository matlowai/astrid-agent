"""Understanding-owned built-in pipeline step."""
from dataclasses import dataclass
from typing import Callable

from astrid.pack_api import executor_argv

STEP_ORDER = ("scene_describe",)

@dataclass(frozen=True)
class Step:
    name: str
    sentinels: tuple[str, ...]
    build_cmd: Callable
    per_brief: bool = False
    always_run: bool = False
    invoke: Callable | None = None


def _scene_describe(args):
    return [
        *executor_argv("understanding.scene_describe", args.python_exec),
        "--scenes", str(args.out / "scenes.json"),
        "--triage", str(args.out / "scene_triage.json"),
        "--video", str(args.video), "--out", str(args.out),
        *(["--env-file", str(args.env_file)] if args.env_file else []),
        *args.extra_args.get("scene_describe", []),
    ]


def build_pool_steps():
    return [Step("scene_describe", ("scene_descriptions.json",), _scene_describe)]


def prepare_brief_artifacts(args):
    """Scene description does not consume or modify the brief."""
