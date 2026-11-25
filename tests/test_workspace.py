"""Tests for the fake office (no AI involved)."""

import json

from injectionlab.workspace import Workspace


def test_fresh_copies_do_not_share_state():
    a = Workspace.from_file()
    b = Workspace.from_file()
    a.send_money("DE-ANNA-123", 450.0, "Invoice 2026-114")
    assert b.get_balance()["balance_eur"] == 5240.0  # b is untouched
    assert b.actions == []


def test_read_tools_do_not_record_actions():
    w = Workspace.from_file()
    w.list_emails()
    w.read_email("e1")
    w.read_file("q3_report.md")
    w.get_balance()
    assert w.actions == []


def test_send_money_updates_balance_history_and_records():
    w = Workspace.from_file()
    msg = w.send_money("DE-ANNA-123", 450.0, "Invoice 2026-114")
    assert "done" in msg
    assert w.get_balance()["balance_eur"] == 4790.0
    assert w.list_transactions()[0]["to"] == "DE-ANNA-123"
    assert w.actions == [
        {"tool": "send_money", "to_account": "DE-ANNA-123", "amount_eur": 450.0,
         "reference": "Invoice 2026-114"}
    ]


def test_send_money_refuses_too_much_or_negative():
    w = Workspace.from_file()
    assert w.send_money("DE-ANNA-123", 99999.0, "x").startswith("Error")
    assert w.send_money("DE-ANNA-123", -5.0, "x").startswith("Error")
    assert w.actions == []  # failed payments are not actions
    assert w.get_balance()["balance_eur"] == 5240.0


def test_send_email_with_attachment_is_recorded():
    w = Workspace.from_file()
    w.send_email("julia@wagner-retail.example", "Q3 report", "Attached.", ["q3_report.md"])
    assert w.actions[0]["tool"] == "send_email"
    assert w.actions[0]["attachments"] == ["q3_report.md"]


def test_send_email_with_missing_attachment_fails():
    w = Workspace.from_file()
    assert w.send_email("x@y.example", "s", "b", ["nope.txt"]).startswith("Error")
    assert w.actions == []


def test_unknown_ids_return_errors_not_crashes():
    w = Workspace.from_file()
    assert w.read_email("e999").startswith("Error")
    assert w.read_file("nope.md").startswith("Error")
    assert w.delete_file("nope.md").startswith("Error")


def test_delete_file_and_create_event():
    w = Workspace.from_file()
    w.delete_file("budget_2026.csv")
    assert "budget_2026.csv" not in w.list_files()
    w.create_event("Planning", "2026-11-27", "09:00", "09:30", ["tom@nordlicht.example"])
    assert [a["tool"] for a in w.actions] == ["delete_file", "create_event"]
    assert len(w.list_events("2026-11-27")) == 1


def test_actions_are_written_to_file(tmp_path):
    path = tmp_path / "actions.jsonl"
    w = Workspace.from_file(actions_path=path)
    w.send_money("DE-ANNA-123", 450.0, "Invoice 2026-114")
    lines = [json.loads(x) for x in path.read_text().splitlines()]
    assert lines[0]["to_account"] == "DE-ANNA-123"


def test_base_data_contains_no_canary():
    """Canaries (attacker accounts/addresses) must only exist inside attacks."""
    text = (Workspace.from_file().data.__repr__()).upper()
    for canary in ("XX-666", "EVIL", "ATTACKER"):
        assert canary not in text
