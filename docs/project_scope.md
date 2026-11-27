# Project Scope — P35: Agricultural Knowledge Navigator

## 1. Team Assignment & Project Number Calculation
- **Group ID:** Group_92
- **Repository Name:** `conversational-ai-p35`
- **Allotted Project Number:** **P35**

| Member Name | BITS ID | Last 4 Numerical Digits |
|---|---|---|
| Ravi | `2025aa05029` | `A = 5029` |
| Pritish | `2025aa05686` | `B = 5686` |
| Siddarth | `2025aa05446` | `C = 5446` |
| Abhinav | `2025aa05473` | `D = 5473` |

**Formula Calculation:**
- `A + B + C + D = 5029 + 5686 + 5446 + 5473 = 21634`
- `21634 mod 50 = 34`
- `P = (21634 mod 50) + 1 = 34 + 1 = 35` -> **P35**

## 2. Exact Appendix-A Assignment
- **Project Number & Title:** P35 — *Agricultural Knowledge Navigator*
- **Appendix-A Problem Statement:** Retrieve from permitted crop-care educational documents, ask clarification about crop type and give cited, non-prescriptive information. (`L6`, `L7–L8`)
- **Suggested Stack:** Python, Chroma, LLM (with offline `local-only` deterministic grounded composition)
- **Syllabus Scope:**
  - **Core Workflow (L1–L3):** Input normalization & validation, explicit goal/action decision loop, controlled structured response schema, multi-turn conversation state read/update (crop-type clarification continuity), structured JSON turn tracing, and error handling.
  - **Selected Capability 1 — L6 (Semantic Retrieval):** Deterministic chunking and indexing of permitted crop-care educational documents using local `sentence-transformers` embeddings (`all-MiniLM-L6-v2`) and a persistent local `Chroma` vector store, with top-$k$ retrieval, crop-type metadata filtering, similarity thresholding, and stable source IDs.
  - **Selected Capability 2 — L7–L8 (Grounded RAG):** Evidence-only answer composition with inline section/document citations (`[DOC-ID § Section]`), non-prescriptive educational framing, post-generation citation validation, and explicit refusal when retrieved evidence is absent or below the similarity threshold.

## 3. Target Users & Problem Statement
- **Target Users:** Agricultural students, extension trainees, smallholder growers seeking general educational crop-care concepts, and instructors/evaluators exploring grounded agricultural Q&A.
- **Problem:** General agricultural queries (e.g., *"Why are my leaves turning yellow?"* or *"How should irrigation be managed during flowering?"*) are often underspecified without knowing the crop type, and free-form chatbots risk hallucinating chemical dosages or unverified advice. A conversational interface can clarify missing crop context across turns, semantically search a vetted educational corpus, and return concise, cited, non-prescriptive explanations—or explicitly refuse when the corpus does not cover the topic.
- **Why Conversational Interface:** Multi-turn dialogue naturally supports incremental clarification (asking for the missing crop type while preserving the user's original symptom/question) and follow-up questions on the same crop without forcing users to repeat context or construct rigid search queries.

## 4. In-Scope vs. Out-of-Scope (Exclusions)
### In Scope (Phase I)
- Permitted synthetic/educational crop-care corpus covering five representative crops (`wheat`, `rice`, `tomato`, `maize`, `potato`) plus general `soil_irrigation` principles.
- Multi-turn crop-type clarification and active crop context tracking in SQLite per `session_id`.
- Semantic retrieval via Chroma + `sentence-transformers` with score thresholding and metadata filtering.
- Grounded, cited, non-prescriptive educational responses in `local-only` mode (and optional `openai` / `ollama` modes when configured, with citation verification).
- Refusal responses for unsupported crops, off-topic requests, prescriptive pesticide/chemical dosage requests, or low-similarity retrieval hits.

### Explicit Exclusions (Out of Scope / Phase II)
- **No Phase-II (L9–L16) features:** No autonomous multi-agent planning, live weather/soil sensor APIs, real-time regional extension escalation workflows, automated evaluation dashboards, or external ticket/booking actions.
- **No prescriptive advice:** The system does not prescribe chemical pesticide/fungicide/fertilizer brand names, exact chemical mixing dosages, legal compliance determinations, or financial/market decisions.
- **No unverified external web retrieval:** Answers are strictly bounded to the indexed documents in `data/raw/`.

## 5. Measurable Success Criteria
1. **Clarification Accuracy:** Queries missing `crop_type` (e.g., *"yellowing lower leaves"*) trigger `CLARIFY_CROP`, store `pending_query` in SQLite, and seamlessly resolve on the user's crop reply in the next turn (`RETRIEVE_AND_ANSWER`).
2. **Retrieval Grounding & Citation Integrity:** Every grounded answer cites at least one verified `source_id` + `section` present in the top-$k$ retrieved chunks with cosine similarity $\ge 0.32$, and `citation_validation.passed == True`.
3. **Refusal Discipline:** Queries about unindexed topics/crops (e.g., *"dragon fruit pruning in arid zones"* or *"quantum computing"*) or prescriptive chemical dosages return a structured refusal (`REFUSE_INSUFFICIENT_EVIDENCE` or `REFUSE_PRESCRIPTIVE_REQUEST`) with zero fabricated citations.
4. **Offline Reproducibility:** The full FastAPI server, scenario runner (`scripts/run_scenarios.py`), and `pytest` suite pass 100% in `AGRI_LLM_MODE=local-only` with no API keys required.

## 6. Phase-II Enhancement Idea (Plan Only — Not Implemented in Phase I)
- **Localized Information Retrieval and Expert Referral:** Extend the corpus with region/agro-climatic zone metadata, add multi-step regional verification and soil-health context checklists, and integrate a human-in-the-loop agricultural extension officer referral workflow with automated RAG faithfulness scoring (L9–L16).
