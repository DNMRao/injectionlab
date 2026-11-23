# Progress log

Plan: 22 working days, Mon 23 Nov – Thu 17 Dec 2026 (Sundays off).
Checkpoint Sat 5 Dec: Stage 1 done → Stage 2, else polish.

## Week 1 — Stage 1 foundations
- [X] Mon 23 Nov — repo skeleton, Docker services, LLM smoke test, first commit + GitHub
- [ ] Tue 24 Nov — fake workspace data + workspace MCP server (side effects recorded)
- [ ] Wed 25 Nov — docs-search MCP server (Qdrant RAG)
- [ ] Thu 26 Nov — LangGraph agent on both MCP servers + JSONL step logs
- [ ] Fri 27 Nov — ~60 normal tasks + automatic graders
- [ ] Sat 28 Nov — baseline run, utility logged to MLflow

## Later (planned)
- Fri 4 – Sat 5 Dec — Streamlit demo app: attack replay page (no defence vs defence, from saved logs) + results page
- Sat 12 Dec — demo app scan page (LoRA detector, "try it yourself")
- Mon 14 Dec — deploy scan API + demo app + Grafana to the cloud

## Daily notes
### Mon 23 Nov
- Indirect prompt injection: an LLM reads external content (web, files, emails) that
  contains hidden instructions written by a third party. The model cannot reliably tell
  data from instructions, so its behaviour changes in unintended ways.
- Agents are riskier than chatbots: (1) they read much more untrusted content through
  tools, and (2) they can ACT (send email, pay, delete), so a hijack causes real damage,
  not just a wrong answer. System prompts alone do not reliably prevent it.
- Interesting: multimodal injection (instructions hidden in images). Out of scope for
  InjectionLab (text only), possible extension.
- POC (scripts/poc_demo.py, gpt-oss-20b, 5 runs each): no guardrail 5/5 hijacked;
  spotlighting 5/5 hijacked; payment permission 0/5 hijacked but 0/5 task done
  (agent still fooled, asks user to pay XX-666) -> security vs usefulness trade-off.
