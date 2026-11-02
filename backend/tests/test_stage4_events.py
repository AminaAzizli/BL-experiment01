from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_event_batch_is_idempotent_and_metrics_are_derived():
    study_response = client.post("/api/studies", json={"name": "Stage 4 event test"})
    assert study_response.status_code == 200, study_response.text
    study_id = study_response.json()["id"]

    participant_response = client.post(
        f"/api/studies/{study_id}/participants",
        json={"assignment": {"version": "A", "persona": "baseline"}},
    )
    assert participant_response.status_code == 200, participant_response.text
    participant_id = participant_response.json()["participant_id"]

    session_response = client.post(
        "/api/sessions",
        json={"study_id": study_id, "participant_id": participant_id, "ui_language": "en"},
    )
    assert session_response.status_code == 200, session_response.text
    session_id = session_response.json()["session_id"]

    events = [
        {
            "event_id": "evt-stage4-1",
            "event_type": "product_viewed",
            "task_id": "T1",
            "occurred_at": "2026-11-02T10:00:00Z",
            "payload": {"product_id": "book-1"},
        },
        {
            "event_id": "evt-stage4-2",
            "event_type": "task_completed",
            "task_id": "T1",
            "occurred_at": "2026-11-02T10:02:00Z",
            "payload": {"success": True},
        },
    ]
    first_response = client.post(f"/api/sessions/{session_id}/events", json={"events": events})
    assert first_response.status_code == 200, first_response.text
    assert first_response.json() == {"accepted": 2, "duplicates": 0}

    retry_response = client.post(f"/api/sessions/{session_id}/events", json={"events": events})
    assert retry_response.status_code == 200, retry_response.text
    assert retry_response.json() == {"accepted": 0, "duplicates": 2}

    metrics_response = client.get(f"/api/sessions/{session_id}/metrics")
    assert metrics_response.status_code == 200, metrics_response.text
    metrics = metrics_response.json()
    assert metrics["event_count"] == 2
    assert metrics["task_metrics"]["T1"]["duration_seconds"] == 120
    assert metrics["task_metrics"]["T1"]["completed"] is True


def test_event_batch_rejects_unknown_session():
    response = client.post(
        "/api/sessions/missing-session/events",
        json={"events": [{"event_id": "evt-missing", "event_type": "click"}]},
    )
    assert response.status_code == 404
