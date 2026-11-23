"""The single defence interface: check(text, context) -> allow / block / clean.

Every defence (spotlighting, tool permissions, context hygiene, LoRA detector) plugs
into the agent through this one method, so they can be swapped by config and
compared fairly.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class Action(str, Enum):
    ALLOW = "allow"  # pass the text through unchanged
    BLOCK = "block"  # drop the text (agent sees a short notice instead)
    CLEAN = "clean"  # pass a modified version of the text


@dataclass
class CheckContext:
    source: str  # where the text came from, e.g. "tool:read_email" or "user"
    step: int = 0  # agent step number (used by the time analysis in Stage 2)
    user_task: str = ""  # the user's original request
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    action: Action
    text: str  # the text the agent will actually see
    reason: str = ""
    score: float | None = None  # e.g. detector probability


class Defence(Protocol):
    name: str

    def check(self, text: str, context: CheckContext) -> Decision: ...


class NoDefence:
    """Baseline: lets everything through."""

    name = "none"

    def check(self, text: str, context: CheckContext) -> Decision:
        return Decision(Action.ALLOW, text)
