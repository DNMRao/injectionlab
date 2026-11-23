"""Per-step JSONL logger.

One line per agent step (LLM call, tool call, tool output, defence decision),
including the FULL tool output. Every later analysis — attack success, time to
hijack, persistence — is computed from these files, so we never need to re-run
the agent to ask a new question.

Named `tracing` (not `logging`) to avoid confusion with Python's stdlib module.
"""

import json
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any


class StepLogger:
    def __init__(self, runs_dir: str | Path = "runs", run_id: str | None = None):
        self.run_id = run_id or f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        self.path = Path(runs_dir) / self.run_id / "steps.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._steps: dict[str, int] = defaultdict(int)  # step counter per case

    def log(self, case_id: str, kind: str, **data: Any) -> dict:
        record = {
            "run_id": self.run_id,
            "case_id": case_id,
            "step": self._steps[case_id],
            "ts": time.time(),
            "kind": kind,  # e.g. "llm_call", "tool_call", "tool_output", "defence", "final"
            **data,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self._steps[case_id] += 1
        return record

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
