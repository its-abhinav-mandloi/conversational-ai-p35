# Group 92 — Assignment 1 (Phase I) Technical Report Template

> **Instructions for Team:** Export final report as `Group_92_A1_PhaseI_Report.pdf`. All technical facts below are verified from the repository; replace every `[TEAM-TO-FILL]` marker with your own verified screenshots, student commits, and Microsoft Stream timestamps.

---

## 1. Cover Page
- **Course:** Conversational AI (`S1-26_AIMLCZG521`)
- **Assessment:** Assignment 1 — Phase I: Conversational AI System Design and Core Implementation
- **Group ID:** `Group_92`
- **Allotted Project:** `P35 — Agricultural Knowledge Navigator`
- **Group Coordinator:** `[TEAM-TO-FILL]`

| Student Name | BITS ID | Last 4 Numerical Digits |
|---|---|---|
| Ravi | `2025aa05029` | `5029` |
| Pritish | `2025aa05686` | `5686` |
| Siddarth | `2025aa05446` | `5446` |
| Abhinav | `2025aa05473` | `5473` |

- **Project Number Formula:** `((5029 + 5686 + 5446 + 5473) mod 50) + 1 = (21634 mod 50) + 1 = 34 + 1 = 35` -> **P35**

---

## 2. Abstract and Objective
The **Agricultural Knowledge Navigator (P35)** is a local-first, context-aware conversational assistant built with Python, FastAPI, SQLite, SentenceTransformers (`all-MiniLM-L6-v2`), and ChromaDB. It answers crop-care educational queries strictly from a vetted synthetic reference corpus (`wheat`, `rice`, `tomato`, `maize`, `potato`, and general soil/irrigation/IPM fundamentals), detects missing crop context to ask clarifying follow-up questions across turns, cites retrieved document sections (`[DOC-ID#sec-N]`), enforces non-prescriptive educational boundaries, and explicitly refuses when evidence is insufficient.

---

## 3. Problem Statement, Scope, L1–L8 Mapping, Requirements, and Five Use Cases
- See [`docs/project_scope.md`](../docs/project_scope.md) and [`docs/use_cases.md`](../docs/use_cases.md).
- **Selected Capabilities:**
  - **L1–L3 (Core Workflow):** Input normalization, controlled Pydantic response schema, explicit goal/action loop (`CLARIFY_CROP`, `RETRIEVE_AND_ANSWER`, `REFUSE_PRESCRIPTIVE_REQUEST`, `REFUSE_INSUFFICIENT_EVIDENCE`, `GREET_OR_HELP`), SQLite session continuity, JSON turn tracing.
  - **L6 (Semantic Retrieval):** Deterministic frontmatter + section chunking (`24` chunks across `6` docs), local `all-MiniLM-L6-v2` embeddings, Chroma cosine search with `crop_type` filter and `0.32` similarity threshold.
  - **L7–L8 (Grounded RAG):** Evidence-only synthesis with inline `[DOC-ID#sec-N]` citations, post-generation `validate_citations`, non-prescriptive disclaimer, and zero-hallucination refusal on low-similarity/unsupported queries.
- **Phase II Plan Only (Not Implemented):** Localized regional metadata retrieval and human agricultural extension officer referral.

---

## 4. Architecture, Goal/Action Loop, Conversation State, Component Flow, and Trade-Offs
- Include the two Mermaid diagrams and interface/trade-off tables from [`docs/architecture.md`](../docs/architecture.md) and [`docs/technology_choices.md`](../docs/technology_choices.md).

---

## 5. Implementation Details (L1–L3, L6, L7–L8)
- **L1–L3 Orchestrator & State:** `src/agri_navigator/orchestrator.py`, `src/agri_navigator/repository.py`, `src/agri_navigator/api.py`
- **L6 Semantic Retrieval:** `src/agri_navigator/retrieval.py`, `scripts/initialise_data.py`, `data/raw/*.md`
- **L7–L8 Grounded RAG:** `src/agri_navigator/grounded_answer.py`, `src/agri_navigator/domain_data.py`
- `[TEAM-TO-FILL: Add concise code walkthrough notes and local execution screenshots]`

---

## 6. Five Executed Scenarios (Prompts, Actions, Outputs, Citations, Logs)
- Copy verified transcripts and trace excerpts directly from `evidence/transcripts/latest_scenarios.md` and `evidence/transcripts/latest_scenarios.json` (`SC-01` through `SC-05`).
- `[TEAM-TO-FILL: Insert Swagger UI / terminal execution screenshots matching the recorded runs]`

---

## 7. Test Plan, Results (5 Functional + 2 Negative/Edge), and Limitations
- Verified test suite output is recorded in `evidence/test-results/pytest_results.txt` (**20 passed** via `.venv/bin/pytest -v`).
- Scenario runner outputs (`SC-01`–`SC-05`, `NEG-01`, `NEG-02`) are recorded in `evidence/transcripts/latest_scenarios.json`.
- **Observed Limitations & Failure Modes:**
  1. Corpus covers five representative crops (`wheat`, `rice`, `tomato`, `maize`, `potato`) plus general soil/IPM; other crops trigger `REFUSE_INSUFFICIENT_EVIDENCE`.
  2. Crop and prescriptive detection use deterministic pattern/keyword rules rather than an intent-classification fine-tuned model, so paraphrased chemical dosage queries outside regex patterns fall back to retrieval/similarity checks.
  3. Default `local-only` mode produces deterministic extractive summaries rather than abstractive prose (optional `openai` / `ollama` modes require external credentials or running local Ollama daemon).

---

## 8. Four-Person Contribution Matrix, Commit/File References, and Video Timestamps
- Complete from [`CONTRIBUTIONS.md`](../CONTRIBUTIONS.md) after every team member pushes verified commits and records the combined demo:
  - `[TEAM-TO-FILL: Member commit IDs, cross-module reviews, challenges, and mm:ss–mm:ss video timestamps]`

---

## 9. Reproduction Instructions, GitHub URL, Microsoft Stream URL, and References
- **GitHub Repository:** `https://github.com/its-abhinav-mandloi/conversational-ai-p35` (tag `assignment-1`)
- **Microsoft Stream URL:** `[TEAM-TO-FILL — update STREAM_LINK.txt and paste working institutional URL here]`
- **Reproduction Commands:** See [`README.md`](../README.md).

---

## 10. AI-Tool Use Disclosure
- See [`docs/ai_use_disclosure.md`](../docs/ai_use_disclosure.md).
- `[TEAM-TO-FILL: Insert final representative prompt and summary of manual team verification]`
