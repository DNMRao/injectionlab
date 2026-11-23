"""Day-1 tests: the defence interface and the step logger work as promised."""

from injectionlab.defences import Action, CheckContext, NoDefence
from injectionlab.tracing.steplog import StepLogger


def test_no_defence_allows_text_unchanged():
    d = NoDefence().check("hello", CheckContext(source="tool:read_email"))
    assert d.action is Action.ALLOW
    assert d.text == "hello"


def test_step_logger_counts_steps_per_case(tmp_path):
    log = StepLogger(runs_dir=tmp_path, run_id="t1")
    log.log("case-a", "tool_call", tool="send_email")
    log.log("case-a", "tool_output", output="ok")
    log.log("case-b", "tool_call", tool="read_file")

    rows = log.read()
    assert [r["step"] for r in rows] == [0, 1, 0]
    assert rows[1]["output"] == "ok"
    assert (tmp_path / "t1" / "steps.jsonl").exists()
