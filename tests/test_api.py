"""End-to-end FastAPI endpoint tests for /health, /sessions, /chat, /traces, and /docs."""

from __future__ import annotations


def test_health_and_docs_endpoints(api_client) -> None:
    health_resp = api_client.get("/health")
    assert health_resp.status_code == 200
    health = health_resp.json()
    assert health["status"] == "ok"
    assert health["sqlite_ok"] is True
    assert health["chroma_ok"] is True
    assert health["indexed_chunks"] == 24
    assert "wheat" in health["supported_crops"]

    docs_resp = api_client.get("/docs")
    assert docs_resp.status_code == 200


def test_session_lifecycle_chat_and_traces(api_client) -> None:
    create_resp = api_client.post("/sessions")
    assert create_resp.status_code == 201
    session_id = create_resp.json()["session_id"]

    chat_resp = api_client.post(
        "/chat",
        json={
            "session_id": session_id,
            "message": "What is Alternate Wetting and Drying in rice?",
        },
    )
    assert chat_resp.status_code == 200
    body = chat_resp.json()
    assert body["action"] == "RETRIEVE_AND_ANSWER"
    assert body["active_crop_type"] == "rice"
    assert body["refused"] is False
    assert any(c["source_id"] == "DOC-RICE-01#sec-1" for c in body["citations"])
    assert body["trace"]["citation_validation_passed"] is True

    detail_resp = api_client.get(f"/sessions/{session_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["turn_count"] == 1
    assert detail["active_crop_type"] == "rice"
    assert len(detail["messages"]) == 2

    traces_resp = api_client.get(f"/sessions/{session_id}/traces")
    assert traces_resp.status_code == 200
    traces = traces_resp.json()
    assert len(traces) == 1
    assert traces[0]["selected_action"] == "RETRIEVE_AND_ANSWER"
