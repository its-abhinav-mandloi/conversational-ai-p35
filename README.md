# P35: Agricultural Knowledge Navigator

**Course:** Conversational AI (`S1-26_AIMLCZG521`) — Assignment 1, Phase I  
**Group:** Group_92  
**Topic Calculation:** `((5029 + 5686 + 5446 + 5473) mod 50) + 1 = (21634 mod 50) + 1 = 35` -> **P35**

A context-aware, local-first FastAPI conversational assistant that retrieves educational crop-care guidance from a vetted synthetic corpus, asks clarifying questions when crop type is unspecified across turns, synthesizes non-prescriptive answers with inline section citations (`[DOC-ID#sec-N]`), and explicitly refuses unsupported or prescriptive requests.

---

## 1. Implemented Capabilities (L1–L3 + L6, L7–L8)
- **L1–L3 Core Conversation Workflow:**
  - Input normalization & validation (`normalize_user_input`), controlled Pydantic response schema (`ChatResponse`), explicit goal/action decision loop (`CLARIFY_CROP`, `RETRIEVE_AND_ANSWER`, `REFUSE_PRESCRIPTIVE_REQUEST`, `REFUSE_INSUFFICIENT_EVIDENCE`, `GREET_OR_HELP`).
  - Transactional SQLite session state (`active_crop_type`, `pending_clarification`, `pending_query`, bounded message history) and structured JSON `TurnTrace` logging.
- **L6 Semantic Retrieval:**
  - Deterministic frontmatter + markdown section chunker (`24` chunks across `6` synthetic educational documents in `data/raw/`).
  - Local embeddings via `sentence-transformers/all-MiniLM-L6-v2` (with zero-network `hashed-local` fallback option) stored in a persistent `ChromaDB` cosine index (`data/processed/chroma_db`), supporting top-$k$ retrieval, crop-type metadata filtering, and similarity thresholding (`>= 0.32`).
- **L7–L8 Grounded RAG:**
  - Evidence-only answer composition in deterministic `local-only` mode (no API key required) plus optional `openai` and `ollama` adapters that safely fall back to `local-only` if credentials or local servers are unavailable.
  - Post-generation citation verification (`validate_citations`) and mandatory non-prescriptive educational disclaimer.

---

## 2. Repository Structure
```text
├── src/agri_navigator/
│   ├── api.py               # FastAPI routes (/health, /sessions, /chat, /docs)
│   ├── config.py            # Environment-safe Pydantic settings
│   ├── schemas.py           # Typed request, response, citation, and trace models
│   ├── orchestrator.py      # Goal/action decision loop & response validation
│   ├── retrieval.py         # L6 chunking, embeddings, Chroma index & search
│   ├── grounded_answer.py   # L7-L8 grounded RAG & citation validation
│   ├── repository.py        # Transactional SQLite persistence
│   └── domain_data.py       # Crop taxonomy & non-prescriptive safety rules
├── data/raw/                # 6 synthetic educational markdown guides (CC0-1.0)
├── scripts/
│   ├── initialise_data.py   # Deterministic SQLite + Chroma initialization
│   └── run_scenarios.py     # Executes SC-01..SC-05 and NEG-01..NEG-02
├── tests/                   # Deterministic pytest suite (20 tests)
├── evidence/                # Real generated transcripts & pytest logs
├── docs/                    # Scope, architecture, use cases, tech choices, provenance, AI disclosure
└── report/                  # Report template for final PDF assembly
```

---

## 3. Prerequisites & Installation
- Python **3.11+** (tested on Python `3.12.14`)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

*(If `uv` is installed: `uv venv .venv && source .venv/bin/activate && uv pip install -r requirements.txt`.)*

---

## 4. Data Initialization & Running the Server

1. **Build the SQLite database and Chroma vector index:**
```bash
python scripts/initialise_data.py
```

2. **Start the FastAPI server (one documented run command):**
```bash
PYTHONPATH=src uvicorn agri_navigator.api:app --host 127.0.0.1 --port 8000
```

Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

---

## 5. API Usage Examples (Reproducing Multi-Turn Clarification)

```bash
# 1. Check readiness
curl -s http://127.0.0.1:8000/health | python3 -m json.tool

# 2. Create a session
SESSION_ID=$(curl -s -X POST http://127.0.0.1:8000/sessions | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

# 3. Turn 1: Missing crop type triggers CLARIFY_CROP
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"Why are lower leaves turning yellow?\"}" | python3 -m json.tool

# 4. Turn 2: Clarify crop type -> resolves pending query with cited wheat guidance
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"wheat\"}" | python3 -m json.tool

# 5. Inspect persisted session state & structured traces
curl -s http://127.0.0.1:8000/sessions/$SESSION_ID/traces | python3 -m json.tool
```

---

## 6. Running Scenarios, Tests, and Linter

```bash
# Execute all 5 functional scenarios + 2 negative scenarios and save evidence
python scripts/run_scenarios.py

# Run the full deterministic pytest suite
pytest -v

# Run ruff lint checks
ruff check src tests scripts
```

### Evidence Locations
- Scenario transcripts & JSON traces: [`evidence/transcripts/latest_scenarios.md`](evidence/transcripts/latest_scenarios.md) and [`evidence/transcripts/latest_scenarios.json`](evidence/transcripts/latest_scenarios.json)
- Pytest execution log: [`evidence/test-results/pytest_results.txt`](evidence/test-results/pytest_results.txt)
- Architecture & use-case specs: [`docs/architecture.md`](docs/architecture.md), [`docs/use_cases.md`](docs/use_cases.md), [`docs/project_scope.md`](docs/project_scope.md)

---

## 7. Safety, Limitations, and AI Disclosure
- **Non-Prescriptive Safety:** The system provides educational crop-care summaries only and refuses chemical dosage, mixing ratio, or spray-schedule requests.
- **Corpus Scope:** Limited to five crops (`wheat`, `rice`, `tomato`, `maize`, `potato`) plus general soil/irrigation/IPM fundamentals. Unindexed crops and unrelated topics are refused with zero citations.
- **Offline Mode:** Runs offline in `AGRI_LLM_MODE=local-only` once `all-MiniLM-L6-v2` is cached locally. Optional `openai`/`ollama` providers are disabled unless configured and fall back safely if unavailable.
- **AI Disclosure:** See [`docs/ai_use_disclosure.md`](docs/ai_use_disclosure.md).

---

## 8. Team Ownership Completion Steps
Before submitting `Group_92_A1_PhaseI_Report.pdf`:
1. Each member (`Ravi`, `Pritish`, `Siddarth`, `Abhinav`) must review, test, and make real commits for their assigned files in [`CONTRIBUTIONS.md`](CONTRIBUTIONS.md).
2. Record the 12–20 minute group Microsoft Stream demo, update [`STREAM_LINK.txt`](STREAM_LINK.txt), and fill timestamps/commit hashes/screenshots in [`report/REPORT_TEMPLATE.md`](report/REPORT_TEMPLATE.md).
