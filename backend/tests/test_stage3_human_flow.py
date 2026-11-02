from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_human_flow_study_participant_and_session_creation():
    study_response = client.post(
        "/api/studies",
        json={
            "name": "Pilot Study 01",
            "ethics_status": "approved",
            "preregistration_version": "v1",
            "invitation_link": "https://example.com/invite/pilot-01",
        },
    )
    assert study_response.status_code == 200, study_response.text
    study = study_response.json()

    participant_response = client.post(
        f"/api/studies/{study['id']}/participants",
        json={
            "recruitment_source": "email",
            "ui_language": "en",
            "background_questions": {"age_range": "25-34", "device": "desktop"},
            "assignment": {"version": "A", "persona": "baseline"},
        },
    )
    assert participant_response.status_code == 200, participant_response.text
    participant = participant_response.json()
    assert participant["assigned_version"] == "A"

    session_response = client.post(
        "/api/sessions",
        json={
            "study_id": study["id"],
            "participant_id": participant["participant_id"],
            "ui_language": "en",
            "assigned_version": "A",
            "task_instructions": "Browse and complete the cart flow.",
        },
    )
    assert session_response.status_code == 200, session_response.text
    session = session_response.json()
    assert session["status"] == "in_progress"
    assert session["assigned_version"] == "A"
    assert session["actor_type"] == "human"


def test_ai_session_is_explicit_and_does_not_require_a_human_participant():
    study_response = client.post("/api/studies", json={"name": "AI run study"})
    assert study_response.status_code == 200
    study_id = study_response.json()["id"]

    response = client.post(
        "/api/sessions",
        json={
            "study_id": study_id,
            "participant_id": "AI-run-test-001",
            "actor_type": "ai",
            "persona": "neutral_baseline",
            "persona_parameters": {"exploration_level": 0.5, "verification_level": 0.5},
            "model_name": "test-model",
            "run_id": "run-test-001",
            "assigned_version": "B",
            "task_instructions": "Test task",
        },
    )
    assert response.status_code == 200, response.text
    session = response.json()
    assert session["actor_type"] == "ai"
    assert session["persona"] == "neutral_baseline"
    assert session["run_id"] == "run-test-001"

    results_response = client.get("/api/results")
    assert results_response.status_code == 200, results_response.text
    stored_result = next(item for item in results_response.json() if item["session_id"] == session["session_id"])
    assert stored_result["actor_type"] == "ai"
    assert stored_result["persona"] == "neutral_baseline"
    assert stored_result["persona_parameters"]["exploration_level"] == 0.5
    assert stored_result["version"] == "B"
