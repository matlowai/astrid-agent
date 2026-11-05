"""Public APIs for packs that depend on editorial."""

from typing import Any

from . import cut_timeline


def notes_overlap_ratio(prev: Any, curr: Any) -> float:
    from astrid.packs.editorial.actions.editor_review.run import notes_overlap_ratio as implementation

    return implementation(prev, curr)


def plan_next_action(review: dict[str, Any]) -> str:
    from astrid.packs.editorial.actions.editor_review.run import plan_next_action as implementation

    return implementation(review)


__all__ = ["cut_timeline", "notes_overlap_ratio", "plan_next_action"]


def pool_digest(*args, **kwargs):
    from astrid.packs.editorial.actions.arrange.run import pool_digest as implementation
    return implementation(*args, **kwargs)


def validate_editor_notes(*args, **kwargs):
    from astrid.packs.editorial.actions.editor_review.run import _validate_editor_notes as implementation
    return implementation(*args, **kwargs)


def validate_review_payload_shape(*args, **kwargs):
    from astrid.packs.editorial.actions.editor_review.run import _validate_review_payload_shape as implementation
    return implementation(*args, **kwargs)


def arrangement_summary(*args, **kwargs):
    from astrid.packs.editorial.actions.editor_review.run import arrangement_summary as implementation
    return implementation(*args, **kwargs)


def __getattr__(name):
    if name in {"DEFAULT_MODEL", "RESPONSE_SCHEMA"}:
        from astrid.packs.editorial.actions.editor_review import run
        return getattr(run, name)
    raise AttributeError(name)

__all__ += ["pool_digest", "validate_editor_notes", "validate_review_payload_shape", "arrangement_summary", "DEFAULT_MODEL", "RESPONSE_SCHEMA"]
