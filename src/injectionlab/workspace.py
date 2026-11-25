"""The fake office: emails, files, calendar and a bank account.

`Workspace` loads a fresh copy of the office data for every test, offers the tools
the agent can use, and records every action that changes something (sending an
email, paying, creating an event, deleting a file). The judge later checks these
recorded actions, e.g. "was money sent to the attacker's canary account?".

Pure Python, no AI and no MCP here, so it is easy to test. The MCP server
(mcp_servers/workspace_server.py) is a thin layer on top of this class.
"""

import copy
import json
from pathlib import Path
from typing import Any

BASE_DATA = Path(__file__).resolve().parents[2] / "data" / "workspace" / "base.json"


class Workspace:
    def __init__(self, data: dict, actions_path: str | Path | None = None):
        self.data = copy.deepcopy(data)  # own copy: tests never share state
        self.actions: list[dict] = []  # every change, in order
        self.actions_path = Path(actions_path) if actions_path else None

    @classmethod
    def from_file(cls, path: str | Path = BASE_DATA, **kwargs) -> "Workspace":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")), **kwargs)

    # ------------------------------------------------------------ recording
    def _record(self, tool: str, **args: Any) -> None:
        action = {"tool": tool, **args}
        self.actions.append(action)
        if self.actions_path:  # also write to a file, so another process can read it
            self.actions_path.parent.mkdir(parents=True, exist_ok=True)
            with self.actions_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(action, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------ read tools
    def list_emails(self) -> list[dict]:
        """Short overview of the inbox (newest first)."""
        return [
            {"id": e["id"], "from": e["from"], "date": e["date"], "subject": e["subject"]}
            for e in self.data["emails"]
        ]

    def read_email(self, email_id: str) -> dict | str:
        for e in self.data["emails"]:
            if e["id"] == email_id:
                return e
        return f"Error: no email with id '{email_id}'."

    def search_emails(self, query: str) -> list[dict]:
        q = query.lower()
        return [
            {"id": e["id"], "from": e["from"], "date": e["date"], "subject": e["subject"]}
            for e in self.data["emails"]
            if q in (e["subject"] + " " + e["body"] + " " + e["from"]).lower()
        ]

    def list_files(self) -> list[str]:
        return [f["name"] for f in self.data["files"]]

    def read_file(self, name: str) -> str:
        for f in self.data["files"]:
            if f["name"] == name:
                return f["content"]
        return f"Error: no file named '{name}'."

    def list_contacts(self) -> list[dict]:
        return self.data["contacts"]

    def list_events(self, date: str | None = None) -> list[dict]:
        events = self.data["calendar"]
        return [e for e in events if date is None or e["date"] == date]

    def get_balance(self) -> dict:
        b = self.data["bank"]
        return {"account": b["account"], "balance_eur": b["balance_eur"]}

    def list_payees(self) -> dict:
        return self.data["bank"]["payees"]

    def list_transactions(self) -> list[dict]:
        return self.data["bank"]["transactions"]

    # ------------------------------------------------------------ action tools (recorded)
    def send_email(self, to: str, subject: str, body: str, attachments: list[str] | None = None) -> str:
        attachments = attachments or []
        missing = [a for a in attachments if a not in self.list_files()]
        if missing:
            return f"Error: attachment(s) not found: {', '.join(missing)}."
        self._record("send_email", to=to, subject=subject, body=body, attachments=attachments)
        return f"Email sent to {to}."

    def send_money(self, to_account: str, amount_eur: float, reference: str) -> str:
        bank = self.data["bank"]
        if amount_eur <= 0:
            return "Error: amount must be positive."
        if amount_eur > bank["balance_eur"]:
            return "Error: insufficient balance."
        bank["balance_eur"] = round(bank["balance_eur"] - amount_eur, 2)
        bank["transactions"].insert(
            0,
            {
                "date": self.data["user"]["today"],
                "to": to_account,
                "amount_eur": amount_eur,
                "reference": reference,
            },
        )
        self._record("send_money", to_account=to_account, amount_eur=amount_eur, reference=reference)
        return f"Payment of {amount_eur:.2f} EUR to {to_account} done."

    def create_event(
        self, title: str, date: str, start: str, end: str, attendees: list[str] | None = None
    ) -> str:
        event_id = f"c{len(self.data['calendar']) + 1}"
        event = {"id": event_id, "title": title, "date": date, "start": start, "end": end,
                 "attendees": attendees or []}
        self.data["calendar"].append(event)
        self._record("create_event", **{k: v for k, v in event.items() if k != "id"})
        return f"Event '{title}' created on {date} {start}-{end}."

    def delete_file(self, name: str) -> str:
        if name not in self.list_files():
            return f"Error: no file named '{name}'."
        self.data["files"] = [f for f in self.data["files"] if f["name"] != name]
        self._record("delete_file", name=name)
        return f"File '{name}' deleted."
