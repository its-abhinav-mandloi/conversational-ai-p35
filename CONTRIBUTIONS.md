# Team Contribution & Ownership Matrix — Group 92 (P35)

> **Integrity Note:** Initial scaffolding commits created by the coding assistant are repository bootstrap commits and are **not** attributed as individual student commits. Each member must review, adapt/extend, test, commit under their own Git identity, and demonstrate their assigned component in the Microsoft Stream recording before submission.

## Group Members & Project Number Basis
- **Group ID:** Group_92
- **Allotted Topic:** P35 — *Agricultural Knowledge Navigator* (`(5029 + 5686 + 5446 + 5473) mod 50 + 1 = 35`)

## Editable Four-Member Assignment Matrix

| Member | BITS ID | Assigned Component & Files/Functions | Assigned Tests | Cross-Module Review Target | Real Student Commit ID(s) | Technical Challenge Resolved | Video Timestamp |
|---|---|---|---|---|---|---|---|
| **Ravi** | `2025aa05029` | **API Layer & Configuration** (`src/agri_navigator/api.py`, `config.py`, `schemas.py`: `create_app`, `/health`, `/sessions`, `/chat`, Pydantic contracts) | `tests/test_api.py` (`test_health_and_docs_endpoints`, `test_session_lifecycle_chat_and_traces`) | Review `orchestrator.py` & `repository.py` | `[TEAM-TO-FILL]` | `[TEAM-TO-FILL]` | `[mm:ss–mm:ss]` |
| **Pritish** | `2025aa05686` | **Orchestrator & Safety Guardrails** (`src/agri_navigator/orchestrator.py`, `domain_data.py`: `normalize_user_input`, `AgriNavigatorOrchestrator.handle_turn`, prescriptive/out-of-scope rules) | `tests/test_orchestrator.py`, `tests/test_negative_cases.py` | Review `retrieval.py` & `grounded_answer.py` | `[TEAM-TO-FILL]` | `[TEAM-TO-FILL]` | `[mm:ss–mm:ss]` |
| **Siddarth** | `2025aa05446` | **SQLite State Continuity & Scripts** (`src/agri_navigator/repository.py`, `scripts/run_scenarios.py`: `SQLiteRepository`, `record_turn`, `get_traces`) | `tests/test_state_continuity.py` (`test_clarification_flow_preserves_pending_query_and_resolves_on_crop_reply`) | Review `api.py` & `domain_data.py` | `[TEAM-TO-FILL]` | `[TEAM-TO-FILL]` | `[mm:ss–mm:ss]` |
| **Abhinav** | `2025aa05473` | **L6 Semantic Retrieval & L7–L8 Grounded RAG** (`src/agri_navigator/retrieval.py`, `grounded_answer.py`, `scripts/initialise_data.py`, `data/raw/*.md`) | `tests/test_retrieval_and_rag.py` (`test_semantic_retrieval_returns_relevant_section_with_crop_filter`, `test_citation_validator_rejects_missing_or_hallucinated_citations`) | Review `orchestrator.py` & `tests/test_negative_cases.py` | `[TEAM-TO-FILL]` | `[TEAM-TO-FILL]` | `[mm:ss–mm:ss]` |

## Individual Contribution Declaration
We declare that the identified contributions are accurate, code and evaluation evidence are authentic, AI assistance is disclosed, and every member can explain and reproduce their own work.

| Member | BITS ID | Owned Source Files / Tasks | Commit IDs / Evidence | Signature / Date |
|---|---|---|---|---|
| Ravi | `2025aa05029` | `[TEAM-TO-FILL]` | `[TEAM-TO-FILL]` | `[TEAM-TO-FILL]` |
| Pritish | `2025aa05686` | `[TEAM-TO-FILL]` | `[TEAM-TO-FILL]` | `[TEAM-TO-FILL]` |
| Siddarth | `2025aa05446` | `[TEAM-TO-FILL]` | `[TEAM-TO-FILL]` | `[TEAM-TO-FILL]` |
| Abhinav | `2025aa05473` | `[TEAM-TO-FILL]` | `[TEAM-TO-FILL]` | `[TEAM-TO-FILL]` |
