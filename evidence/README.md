# Verification Evidence — P35: Agricultural Knowledge Navigator

This directory separates **generated runtime evidence** from **editable team templates**.

## Generated Evidence (Observed in Workspace)
- `evidence/transcripts/scenarios_<UTC-TIMESTAMP>.json` & `evidence/transcripts/latest_scenarios.json`: Full HTTP responses, citations, warnings, and structured `TurnTrace` records produced by `python scripts/run_scenarios.py` against the FastAPI application in `AGRI_LLM_MODE=local-only` using `sentence-transformers/all-MiniLM-L6-v2` and `ChromaDB`.
- `evidence/transcripts/scenarios_<UTC-TIMESTAMP>.md` & `evidence/transcripts/latest_scenarios.md`: Human-readable formatted transcripts of the 5 functional scenarios (`SC-01` through `SC-05`) and 2 negative/edge scenarios (`NEG-01`, `NEG-02`).
- `evidence/test-results/pytest_results.txt`: Actual terminal output from running `pytest -v` across all 20 deterministic unit and integration tests.

## Separate Templates (Require Team Completion Before Final Submission)
- `report/REPORT_TEMPLATE.md` — Structured 10-section technical report template with `[TEAM-TO-FILL]` slots for screenshots, individual commit IDs, and Microsoft Stream timestamps.
- `CONTRIBUTIONS.md` — Editable four-member ownership matrix template.
- `STREAM_LINK.txt` — Placeholder for the institutional Microsoft Stream demonstration URL.
