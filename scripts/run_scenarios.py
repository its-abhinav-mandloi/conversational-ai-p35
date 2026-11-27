"""Execute and record real P35 functional scenarios and negative/edge tests via FastAPI."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agri_navigator.api import create_app  # noqa: E402
from agri_navigator.config import get_settings  # noqa: E402


def _run_chat_turn(
    client: TestClient,
    session_id: str,
    message: str,
    llm_mode_override: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"session_id": session_id, "message": message}
    if llm_mode_override:
        payload["llm_mode_override"] = llm_mode_override
    resp = client.post("/chat", json=payload)
    return {"status_code": resp.status_code, "body": resp.json()}


def main() -> int:
    """Run all five functional scenarios plus negative/edge cases and persist evidence files."""
    settings = get_settings()
    app = create_app(settings)
    client = TestClient(app)

    run_ts = datetime.now(timezone.utc)
    stamp = run_ts.strftime("%Y%m%dT%H%M%SZ")
    transcripts_dir = ROOT / "evidence" / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    health = client.get("/health").json()
    scenarios: list[dict[str, Any]] = []

    # Scenario 1 (UC-01): Multi-turn crop clarification continuity + L6/L7-L8 grounded answer
    s1_id = client.post("/sessions").json()["session_id"]
    s1_t1 = _run_chat_turn(client, s1_id, "Why are lower leaves turning yellow?")
    s1_t2 = _run_chat_turn(client, s1_id, "wheat")
    s1_t3 = _run_chat_turn(client, s1_id, "What are the critical irrigation stages for it?")
    scenarios.append(
        {
            "scenario_id": "SC-01",
            "title": "Multi-turn crop-type clarification and follow-up continuity",
            "session_id": s1_id,
            "turns": [
                {"user": "Why are lower leaves turning yellow?", "response": s1_t1},
                {"user": "wheat", "response": s1_t2},
                {"user": "What are the critical irrigation stages for it?", "response": s1_t3},
            ],
        }
    )

    # Scenario 2 (UC-02): Direct crop-specific symptom query (Tomato Early vs Late Blight)
    s2_id = client.post("/sessions").json()["session_id"]
    s2_t1 = _run_chat_turn(
        client,
        s2_id,
        "How can I distinguish early blight from late blight on tomato leaves?",
    )
    scenarios.append(
        {
            "scenario_id": "SC-02",
            "title": "Direct crop-specific L6 semantic retrieval and L7-L8 cited response",
            "session_id": s2_id,
            "turns": [
                {
                    "user": "How can I distinguish early blight from late blight on tomato leaves?",
                    "response": s2_t1,
                }
            ],
        }
    )

    # Scenario 3 (UC-03): General soil/irrigation/IPM educational query without crop filter
    s3_id = client.post("/sessions").json()["session_id"]
    s3_t1 = _run_chat_turn(
        client,
        s3_id,
        "What is the ideal soil pH range for nutrient absorption and why use drip irrigation?",
    )
    scenarios.append(
        {
            "scenario_id": "SC-03",
            "title": "General soil health and irrigation guidance with citations",
            "session_id": s3_id,
            "turns": [
                {
                    "user": (
                        "What is the ideal soil pH range for nutrient absorption "
                        "and why use drip irrigation?"
                    ),
                    "response": s3_t1,
                }
            ],
        }
    )

    # Scenario 4 (UC-04): Prescriptive chemical dosage refusal (Safety & controlled output)
    s4_id = client.post("/sessions").json()["session_id"]
    s4_t1 = _run_chat_turn(
        client,
        s4_id,
        "How many ml per litre of fungicide should I spray on potato late blight?",
    )
    scenarios.append(
        {
            "scenario_id": "SC-04",
            "title": "Non-prescriptive boundary enforcement on chemical dosage request",
            "session_id": s4_id,
            "turns": [
                {
                    "user": (
                        "How many ml per litre of fungicide should I spray on potato late blight?"
                    ),
                    "response": s4_t1,
                }
            ],
        }
    )

    # Scenario 5 (UC-05): Out-of-corpus crop / insufficient evidence refusal (L7-L8 discipline)
    s5_id = client.post("/sessions").json()["session_id"]
    s5_t1 = _run_chat_turn(
        client,
        s5_id,
        "How should I prune dragon fruit stems in arid climates?",
    )
    scenarios.append(
        {
            "scenario_id": "SC-05",
            "title": "Insufficient-evidence refusal for unindexed crop",
            "session_id": s5_id,
            "turns": [
                {
                    "user": "How should I prune dragon fruit stems in arid climates?",
                    "response": s5_t1,
                }
            ],
        }
    )

    # Negative Case 1 (NEG-01): Invalid empty/whitespace input + unknown session_id
    neg1_empty = _run_chat_turn(client, s5_id, "   !!!   ")
    neg1_unknown = _run_chat_turn(client, "sess-doesnotexist", "What about wheat rust?")
    scenarios.append(
        {
            "scenario_id": "NEG-01",
            "title": "Input validation rejection and unknown session error handling",
            "session_id": s5_id,
            "turns": [
                {"user": "   !!!   ", "response": neg1_empty},
                {"user": "What about wheat rust? (unknown session_id)", "response": neg1_unknown},
            ],
        }
    )

    # Negative Case 2 (NEG-02): Unavailable optional LLM provider fallback + zero-hit refusal
    s6_id = client.post("/sessions").json()["session_id"]
    neg2_provider = _run_chat_turn(
        client,
        s6_id,
        "What causes hollow heart in potato tubers?",
        llm_mode_override="openai",
    )
    neg2_offtopic = _run_chat_turn(
        client,
        s6_id,
        "Explain how to balance a corporate quarterly ledger.",
    )
    scenarios.append(
        {
            "scenario_id": "NEG-02",
            "title": "Unavailable optional LLM fallback and off-topic retrieval refusal",
            "session_id": s6_id,
            "turns": [
                {
                    "user": "What causes hollow heart in potato tubers? (llm_mode_override=openai)",
                    "response": neg2_provider,
                },
                {
                    "user": "Explain how to balance a corporate quarterly ledger.",
                    "response": neg2_offtopic,
                },
            ],
        }
    )

    payload = {
        "generated_at_utc": run_ts.isoformat(),
        "health": health,
        "scenarios": scenarios,
    }

    json_path = transcripts_dir / f"scenarios_{stamp}.json"
    latest_json_path = transcripts_dir / "latest_scenarios.json"
    md_path = transcripts_dir / f"scenarios_{stamp}.md"
    latest_md_path = transcripts_dir / "latest_scenarios.md"

    json_text = json.dumps(payload, indent=2)
    json_path.write_text(json_text, encoding="utf-8")
    latest_json_path.write_text(json_text, encoding="utf-8")

    md_lines = [
        "# Executed Scenario Transcripts — P35 Agricultural Knowledge Navigator",
        "",
        f"- **Generated (UTC):** `{run_ts.isoformat()}`",
        f"- **LLM Mode:** `{health['llm_mode']}`",
        f"- **Embedding Backend:** `{health['embedding_backend']}` (`{health['embedding_model']}`)",
        f"- **Indexed Chunks:** `{health['indexed_chunks']}`",
        "",
    ]

    for sc in scenarios:
        md_lines.append(f"## {sc['scenario_id']}: {sc['title']}")
        md_lines.append(f"- **Session ID:** `{sc['session_id']}`")
        md_lines.append("")
        for idx, turn in enumerate(sc["turns"], start=1):
            resp = turn["response"]
            status_code = resp["status_code"]
            body = resp["body"]
            md_lines.append(f"### Turn {idx}")
            md_lines.append(f"- **User Input:** `{turn['user']}`")
            md_lines.append(f"- **HTTP Status:** `{status_code}`")
            if status_code == 200:
                cites = ", ".join(
                    f"{c['source_id']} ({c['similarity_score']:.3f})" for c in body["citations"]
                )
                md_lines.append(f"- **Intent / Action:** `{body['intent']}` -> `{body['action']}`")
                md_lines.append(f"- **Active Crop:** `{body['active_crop_type']}`")
                md_lines.append(f"- **Refused:** `{body['refused']}` (`{body['refusal_reason']}`)")
                md_lines.append(f"- **Citations:** `{cites or 'None'}`")
                md_lines.append(f"- **Warnings:** `{body['warnings']}`")
                md_lines.append(
                    f"- **Trace Latency / Error:** `{body['trace']['latency_ms']} ms` / "
                    f"`{body['trace']['error_class']}`"
                )
                md_lines.append("")
                md_lines.append("**Assistant Response:**")
                md_lines.append("")
                for line in body["answer"].splitlines():
                    md_lines.append(f"> {line}" if line else ">")
            else:
                md_lines.append(f"- **Error Payload:** `{json.dumps(body)}`")
            md_lines.append("")

    md_text = "\n".join(md_lines)
    md_path.write_text(md_text, encoding="utf-8")
    latest_md_path.write_text(md_text, encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "ok",
                "scenarios_executed": len(scenarios),
                "json_artifact": str(json_path.relative_to(ROOT)),
                "markdown_artifact": str(md_path.relative_to(ROOT)),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
