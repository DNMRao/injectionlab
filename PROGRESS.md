# Progress log

Plan: 22 working days, Mon 23 Nov – Thu 17 Dec 2026 (Sundays off).
Checkpoint Sat 5 Dec: Stage 1 done → Stage 2, else polish.

## Week 1 — Stage 1 foundations
- [X] Mon 23 Nov — repo skeleton, Docker services, LLM smoke test, first commit + GitHub
- [X] Tue 24 Nov — fake workspace data + workspace MCP server (side effects recorded)
- [X] Wed 25 Nov — docs-search MCP server (Qdrant RAG)
- [X] Thu 26 Nov — LangGraph agent on both MCP servers + JSONL step logs
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
- AgentDojo (arXiv:2406.13352) scores: benign utility, utility under attack, targeted
  attack success rate (ASR). We use the same three, so results are comparable.
- How we differ from the original AgentDojo paper: tools run as MCP servers (it uses its
  own tool runtime); time analysis inside one run (when hijacked, how long the attack
  persists, recovery); head-to-head context-hygiene variants; deployed scan API + demo app.
  NOT a difference: AgentDojo also tested a detector model.
- Interview line: "I use AgentDojo's three metrics so results are comparable, but run the
  tools as MCP servers and add a time analysis: when the agent gets hijacked, how long the
  attack persists, and whether context hygiene helps it recover."

### Tue 24 Nov
- Built the fake office (data/workspace/base.json): user Lena Hoffmann, 8 emails,
  5 files, 3 calendar events, bank account (5240 EUR, 3 saved payees). All fake,
  `.example` domains. No canary (XX-666) in the clean data; canaries only appear in attacks.
- `Workspace` class (src/injectionlab/workspace.py): 10 read tools + 4 action tools
  (send_email, send_money, create_event, delete_file). Every action follows
  check -> change -> record -> confirm. Failed actions are not recorded. Errors are
  returned as "Error: ..." text, so the agent sees them instead of crashing.
- Each test case gets a fresh copy of the office (deepcopy), so runs never share state.
- No recipient/payee check in send_money/send_email on purpose: the office must be
  attackable, otherwise we cannot measure attacks. Protection belongs to the guardrails.
- Actions are also written to a JSONL file ("flight recorder"): the MCP server runs as a
  separate process and its memory is lost when it stops; the judge reads the file.
- MCP server (workspace_server.py): thin layer, 14 tools, labelled READ or ACT
  (readOnlyHint / destructiveHint). The docstrings are what the model reads to choose tools.
  The ACT label will be used by the tool-permission guardrail.
- MCP SDK v2: `MCPServer` (FastMCP was renamed), client is `mcp.Client`.
  `Client(build_server(office))` = in-process (tests), `Client(StdioServerParameters(...))`
  = server started as a separate program (real setup).
- Settings reach the server via environment variables (the only way into a new process):
  INJECTIONLAB_WORKSPACE (which office, default clean base.json) and
  INJECTIONLAB_ACTIONS (where to record). `NAME=value cmd` sets it for one command only;
  in Python: env={**os.environ, "NAME": value}.
- Tests: 15 pass (2 foundations + 10 office + 3 MCP server).

### Wed 25 Nov (finished Thu morning)
- RAG = look things up before answering. Embedding model (BAAI/bge-small-en-v1.5, 384 numbers,
  CPU, via fastembed without PyTorch) turns text into vectors; similar meaning -> small angle
  (cosine similarity). Model name is a setting (EMBED_MODEL) -> MiniLM vs bge comparison later.
- 15 fake company documents (data/docs/), same world as the office. Some contain safety rules
  (e.g. "changed bank details: call the supplier") -> does RAG make the agent safer?
- Chunking at "##" sections: 15 docs -> 56 chunks. Title + heading glued in front before
  embedding, so short chunks keep their context. `pos` keeps the order for read_doc.
- DocsLibrary: build (delete old collection first -> no ghost cards), search (query_points),
  list_docs, read_doc (rebuilt from Qdrant -> search and read always see the same library).
- Qdrant upgraded v1.13.2 -> v1.20.0 to match the client (versions may differ by max 1 minor).
  Index is a cache: always rebuildable from the .md files in git.
- docs MCP server: 3 read-only tools. Does not build the index; DOCS_COLLECTION chooses which
  library (clean or poisoned) -> same server code for attack runs. k clamped to 1-10.
- Poisoned document = more dangerous than poisoned email: the search engine picks it, and it
  can match many questions ("poisoning the well").
- Tests: 31 pass. Qdrant ":memory:" for tests (no Docker), module fixtures, parametrize.

### Thu 26 Nov (finished Fri morning)
- Agent = LangGraph loop of 2 nodes: `agent` (LLM thinks) and `tools` (runs the tool calls).
  State = the conversation (MessagesState). `route()` is the conditional edge: tool calls ->
  tools, none -> END. Fixed edge tools -> agent closes the loop (ReAct pattern).
  `recursion_limit` 20 = max ~10 think/act rounds. The loop is hidden inside `ainvoke`.
- Experiments: no tools->agent edge -> graph stops silently after tools; empty AI reply -> END.
- `langchain-mcp-adapters` needs mcp < 2.0 (ImportError with mcp 2.3) -> wrote our own
  bridge (agent/mcp_tools.py): one MCP Client per server, each MCP tool -> LangChain
  StructuredTool (closure remembers client + tool name). Metadata {server, read_only} is
  kept for guardrails and logs. Duplicate tool names across servers -> error.
  AsyncExitStack closes all connections together. 17 tools (14 workspace + 3 docs).
- System prompt is neutral on purpose (no security warning): it is the baseline.
- Unknown tool name -> "Error: there is no tool ..." returned to the model, not a crash.
- Step log (runs/<run_id>/steps.jsonl): task, llm_call (turn, seconds, tokens, tool calls),
  tool_call (args, server, read_only), tool_output (FULL text), final. Actions file in the
  same run folder. scripts/run_agent.py prints the table FROM the log file -> the log alone
  is enough to replay a run (no API cost, needed for time analysis + demo replay page).
- Real runs: "pay Anna's invoice" -> keyword search found nothing, agent recovered via
  list_emails -> paid 450 EUR to DE-ANNA-123 (1 action recorded). "Q3 report" -> agent
  searched the data-protection doc and asked Martin for approval: RAG rules were followed.
- Retry: ChatOpenAI(max_retries=6) -> openai client retries temporary errors (429, 408,
  409, 5xx, connection) with exponential backoff 0.5 -> 8 s + jitter (~23 s max); wrong key
  or model fails at once. Wait time is inside the logged `seconds`. Not yet seen triggering.
- Tests: 35 pass. Fake LLM (GenericFakeChatModel + bind_tools returns self) follows a fixed
  script -> agent tests without API cost. In-process MCP servers, Qdrant ":memory:".
