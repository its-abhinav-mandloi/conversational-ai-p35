# AI-Tool Use Disclosure — Group 92 (P35: Agricultural Knowledge Navigator)

## 1. Disclosure Statement
AI coding assistance (Google Antigravity / Gemini) was used during Phase I development as an engineering productivity aid. In accordance with course academic-integrity rules, all four team members must personally **review, understand, adapt, execute, test, and defend** every component, design choice, and claim in this repository before final submission and during the Microsoft Stream demonstration.

## 2. Scope of AI Assistance Used
| Area | Purpose of AI Assistance | What the Team Must Verify & Own |
|---|---|---|
| Project scaffolding & FastAPI routes | Drafted `src/agri_navigator/api.py`, `config.py`, and `schemas.py` structure | Verify route contracts, error status codes, and environment variable handling |
| Core orchestrator & persistence | Drafted `orchestrator.py` goal/action loop and `repository.py` SQLite queries | Review decision transitions, state read/write points, and SQL parameterization |
| L6 & L7–L8 modules | Drafted `retrieval.py` Chroma ingestion/search and `grounded_answer.py` citation checks | Validate chunking determinism, similarity threshold (`0.32`), and refusal rules |
| Synthetic corpus & tests | Drafted initial 6 synthetic crop-care markdown guides and `tests/*.py` | Audit agricultural accuracy, licensing notes, and test coverage |
| Documentation templates | Drafted `docs/*.md`, `README.md`, and `report/REPORT_TEMPLATE.md` | Fill team-specific fields, add real screenshots/commits, and verify claims |

## 3. Team Verification Checklist (To Be Completed by Members)
- [ ] Every team member has read and executed their assigned module locally.
- [ ] Every team member has made real, verified Git commits reflecting their adaptations/tests.
- [ ] Every screenshot, commit ID, and video timestamp in the final PDF report was directly observed by the team.

## 4. Representative Prompt Slot
> **[TEAM-TO-FILL — Final Representative Prompt / Refinement Summary]:**
> *Paste or summarize the final representative prompt(s) and key manual refinements made by the team here before exporting `Group_92_A1_PhaseI_Report.pdf`.*
