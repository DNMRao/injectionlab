"""Defences. Every defence implements the same interface (see base.py)."""

from injectionlab.defences.base import Action, CheckContext, Decision, Defence, NoDefence

__all__ = ["Action", "CheckContext", "Decision", "Defence", "NoDefence"]
