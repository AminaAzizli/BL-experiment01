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
