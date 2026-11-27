# Antigravity implementation prompt

Before pasting, replace every value in the **Configuration** block. `PROJECT_NUMBER` is mandatory: calculate it from the four BITS IDs as required by the brief: `((A + B + C + D) mod 50) + 1`, formatted as `P01` to `P50`.

```text
You are the implementation agent for a university Conversational AI Assignment 1, Phase I. Work directly in the currently open project folder. Deliver a complete, runnable, well-tested Python project and push it to GitHub only after the quality gates below pass.

CONFIGURATION - values supplied by the team
- PROJECT_NUMBER: PXX                 # Mandatory. Example: P16. Use the exact Appendix-A domain/challenge for this row.
- GROUP_ID: Group_XX
- REPOSITORY_NAME: conversational-ai-pxx
- REPOSITORY_VISIBILITY: private       # Change to public only if the team wants a public repository.
- EXISTING_GITHUB_REMOTE: <URL or leave blank>
- TEAM_MEMBERS: [name | BITS ID] x 4  # Keep blanks as placeholders; never invent names, IDs, commits, or video times.
- OPTIONAL_LLM_MODE: local-only        # Valid values: local-only, openai, ollama. The application must still run in local-only mode.

FIRST: READ AND INTERPRET THE BRIEF
1. Locate and read the assignment brief in the workspace. It may be a PDF or DOCX. Treat it as the source of truth.
2. Confirm the configured `PROJECT_NUMBER` is P01-P50. Locate that exact Appendix-A row and implement its stated domain and mandatory Phase-I challenge. Do not substitute a different topic.
3. In a concise `docs/project_scope.md`, record the calculation/result supplied by the team, the exact project title, target users, problem, exclusions, measurable success criteria, and Phase-II idea. If the project number is absent or invalid, stop and ask for it before creating domain-specific code.
4. Implement L1-L3 and exactly two evidenced capabilities from L4-L8 appropriate to that row. Do not add Phase-II L9-L16 features. Examples:
   - Rows marked L4/L5: implement validated local tool/function calling and durable multi-turn memory.
   - Rows marked L5/L6: implement durable multi-turn memory and semantic retrieval.
   - Rows marked L6/L7-L8: implement semantic retrieval and grounded RAG with source citations and a refusal when evidence is inadequate.
   Treat “L7-L8” as the grounded-RAG capability, not as a vague label. Show the retrieval-to-answer path in logs and tests.

NON-NEGOTIABLE INTEGRITY AND SAFETY RULES
- Build real, understandable, group-owned code. Do not copy a repository, fabricate screenshots, test results, transcripts, commits, team contributions, model performance, or video timestamps.
- Use only synthetic or permitted public data. Store a short provenance/license note for every included dataset or reference document.
- Never commit API keys, passwords, tokens, personal data, or `.env`. Add `.env.example` with placeholders and a robust `.gitignore`.
- Do not make real purchases, bookings, support tickets, health/legal/financial decisions, or other external actions. Use clearly labeled local mock tools where the assignment requires tools.
- Do not claim a hosted model or external API is required for the app to work. The default local-only mode must be demonstrable offline after dependencies/models are installed. Optional providers must be disabled safely when their credentials are absent.
- Preserve the supplied brief. Do not edit it.

IMPLEMENTATION OBJECTIVE
Create a specific, context-aware conversational application for the assigned PXX topic. It must be runnable by an evaluator with one documented command and must visibly demonstrate:
- input normalization and validation;
- controlled responses (structured response schema, allowed intents/actions, confidence/evidence handling, and safe fallback);
- an explicit goal/action decision loop rather than a hard-coded list of canned replies;
- multi-turn conversation state read and update;
- the two selected L4-L8 capabilities, with concrete runtime evidence for each;
- useful error handling for invalid input, unknown IDs/records, missing slots, no retrieval hits, and unavailable optional LLM providers.

PREFERRED ARCHITECTURE - tailor it to the assigned row; do not add needless frameworks
- Python 3.11+ package under `src/` with clear domain, application, and infrastructure boundaries.
- FastAPI backend with typed Pydantic request/response models and `/health`, `/sessions`, `/chat`, and `/docs` endpoints. A simple CLI or minimal Streamlit UI is acceptable as an additional interface, but the FastAPI API must be sufficient to reproduce every scenario.
- SQLite for durable session state, user preferences/slots, message history, and trace events. Use a new `session_id` per user/session, transactions, and parameterized SQL.
- Local deterministic mock tools for L4 capabilities. Validate tool name and argument schema before invocation; return typed results and never execute arbitrary input as code or SQL.
- For L5, persist a compact facts/slots memory and a bounded message history. The orchestrator must retrieve relevant retained facts on a later turn; merely echoing the immediately previous message is not enough.
- For L6, use local semantic embeddings (for example sentence-transformers) plus a local vector index (FAISS or Chroma) over small permitted/synthetic source documents. Include deterministic ingestion/chunking, stable source IDs, top-k retrieval, score thresholding, and citations.
- For L7-L8, compose answers only from the retrieved context; include source IDs/page-or-section references in the response. If an optional LLM is configured, pass only retrieved context and validate citations after generation. In local-only mode, use a deterministic extractive/template-based grounded answer so the application remains runnable without a key.
- Produce structured JSON logs/traces for each turn that identify intent, selected action, memory reads/writes, tool calls, retrieval candidates/scores, chosen sources, validation result, latency, and error class. Never log secrets.

CREATE THIS REPOSITORY STRUCTURE (adapt filenames only when the assigned topic makes a clearer name necessary)
.
├── src/<package_name>/
│   ├── api.py                 # FastAPI application and routes
│   ├── config.py              # environment-safe configuration
│   ├── schemas.py             # typed inputs, outputs, and trace schema
│   ├── orchestrator.py        # goal/action loop and response validation
│   ├── memory.py              # L5 state persistence/retrieval when selected
│   ├── tools.py               # allowlisted validated local tools when L4 is selected
│   ├── retrieval.py           # ingestion/index/search when L6 is selected
│   ├── grounded_answer.py     # RAG composition/citation validation when L7-L8 is selected
│   ├── repository.py          # SQLite data access
│   └── domain_data.py         # safe synthetic/permitted seed data
├── data/
│   ├── raw/                   # permitted source materials only
│   └── processed/             # generated indexes ignored or rebuilt by script
├── scripts/
│   ├── initialise_data.py     # deterministic seed/index build
│   └── run_scenarios.py       # executes and records the five real scenarios
├── tests/
│   ├── test_orchestrator.py
│   ├── test_memory.py
│   ├── test_tools_or_retrieval.py
│   ├── test_api.py
│   └── test_negative_cases.py
├── evidence/
│   ├── transcripts/           # outputs actually generated by run_scenarios.py
│   ├── test-results/          # actual pytest and scenario result logs
│   └── README.md              # clearly distinguishes generated evidence from templates
├── docs/
│   ├── project_scope.md
│   ├── architecture.md
│   ├── use_cases.md
│   ├── technology_choices.md
│   ├── data_provenance.md
│   └── ai_use_disclosure.md
├── report/
│   └── REPORT_TEMPLATE.md     # report structure and empty team-specific fields only
├── README.md
├── CONTRIBUTIONS.md           # honest four-member ownership matrix template
├── STREAM_LINK.txt            # placeholder only; no invented URL
├── requirements.txt
├── .env.example
├── .gitignore
└── pyproject.toml or pytest.ini

DOCUMENTATION AND EVIDENCE REQUIREMENTS
1. `docs/use_cases.md` must contain at least five genuinely distinct scenarios. Each must state scenario ID, goal, user input and prior context, expected orchestrator action, expected response, measurable success condition, and mapped lessons. Include at least one true multi-turn continuity scenario and at least one scenario for each selected capability.
2. `docs/architecture.md` must provide two readable Mermaid diagrams:
   - overall user input -> preprocessing -> orchestrator/decision loop -> memory/tool/retrieval -> output validation -> response/logging;
   - component/data-flow diagram with storage and the exact read/update points for conversation state.
   It must also define each component interface and explain latency, reliability, and cost trade-offs.
3. `docs/technology_choices.md` must explain why the selected Python framework, datastore, model/embedding approach, and the two capabilities fit this topic. State the offline fallback.
4. Create a short `report/REPORT_TEMPLATE.md` that follows the brief's required report order. Fill only facts verified by the repository. Keep group names, BITS IDs, individual commit IDs, video timestamps, Stream URL, screenshots, and unexecuted test outcomes as clearly marked team-completion fields rather than fabricated content.
5. `CONTRIBUTIONS.md` must divide meaningful components among four members as editable assignments, with fields for owned files/functions, tests, cross-module review, real commit IDs, technical challenge, and video timestamp. Do not attribute automated commits to specific students.
6. `docs/ai_use_disclosure.md` must truthfully state that AI assistance was used, what it helped draft, and that the team must review, adapt, execute, test, understand, and defend every part. Include a slot for the final representative prompt; do not make claims about actions not actually taken.

TESTING AND EXECUTION GATES
- Implement at least seven documented executions: five functional tests covering the five scenarios and both selected capabilities, plus two negative/edge tests. Include continuity failure or tool/retrieval failure where relevant.
- Add deterministic pytest tests for happy paths, state continuity, selected capability behavior, invalid/empty input, unknown resource/tool arguments, and insufficient/no retrieval evidence.
- Run `scripts/initialise_data.py`, then start the application or use its test client, then run `scripts/run_scenarios.py`. Save the actual date/time-stamped transcripts and traces under `evidence/`; label any sample templates separately.
- Run the full test suite. Do not report a test as passed unless it ran successfully in this workspace. Capture the exact command and result in `evidence/test-results/`.
- Fix failures, lint/type errors, broken imports, and setup defects before committing. Verify that a clean clone can install dependencies, initialize data, run tests, and start the server using only the README commands.
- The README must cover project purpose, allotted topic PXX, architecture, prerequisites, installation, environment setup, data initialization, run commands, API examples, scenario command, tests, evidence locations, limitations, safety, AI disclosure, and real team ownership completion steps.

GIT AND GITHUB WORKFLOW
1. Inspect the existing repository first. Preserve unrelated files and existing history. If it is not a Git repository, initialize one on branch `main`.
2. Make small, meaningful local commits only after the corresponding code/tests pass. Suggested commit boundaries: scaffold/config; core conversation and persistence; selected capabilities; tests/evidence/docs. Do not create fake per-student commits or backdate commits.
3. Before any push, run `git status`, inspect the staged diff, scan tracked files for likely secrets, and verify `.env` is ignored. Never use `--force`, never overwrite a remote, and never alter unrelated branches.
4. If `EXISTING_GITHUB_REMOTE` is supplied, configure/verify `origin` and push `main`. If it is blank and GitHub CLI is authenticated, create a repository named `REPOSITORY_NAME` with `REPOSITORY_VISIBILITY`, set `origin`, and push. If neither condition is true, finish the local commits and give the exact safe command the team must run to set the remote; do not pretend it was pushed.
5. After all verification passes, create annotated tag `assignment-1` with a truthful message and push the tag. If the push did not occur, do not claim the tag is remote.

FINAL RESPONSE FORMAT
Return a concise completion report containing:
- assigned project number/title and selected L4-L8 capabilities;
- files and evidence created;
- exact commands executed and actual test outcome;
- commit hashes created, current branch, remote URL, and whether `assignment-1` was pushed;
- any unavoidable manual steps (group IDs, report screenshots, member ownership, Stream link) that must be completed by the team.

Do not stop at a plan. Implement, run, test, document, commit, and push when authenticated/authorized. If a configuration value is genuinely required (especially PXX), ask one focused question before domain-specific implementation; otherwise use sound engineering judgment and proceed.
```
