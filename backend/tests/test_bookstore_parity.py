from copy import deepcopy

from fastapi.testclient import TestClient

from app.bookstore import check_catalog_parity
from app.main import app


client = TestClient(app)


def test_versions_use_same_catalog_and_real_parity_validation():
    response = client.get("/api/bookstore/versions")
    assert response.status_code == 200
    payload = response.json()

    assert payload["version_a"]["products"] == payload["version_b"]["products"]
    assert payload["parity_check"]["status"] == "passed"
    assert all(payload["parity_check"]["checks"].values())


def test_parity_checker_detects_price_and_description_mismatches():
    baseline = client.get("/api/bookstore/versions").json()["version_a"]["products"]
    altered = deepcopy(baseline)
    altered[0]["price"] += 1
    price_result = check_catalog_parity(baseline, altered, ["search", "add_to_cart"], ["search", "add_to_cart"])
    assert price_result["status"] == "failed"
    assert price_result["checks"]["prices"] is False
    assert "price" in " ".join(price_result["issues"]).lower()

    altered = deepcopy(baseline)
    altered[0]["description"] = "Different description"
    description_result = check_catalog_parity(
        baseline,
        altered,
        ["search", "add_to_cart"],
        ["search", "add_to_cart"],
    )
    assert description_result["status"] == "failed"
    assert description_result["checks"]["descriptions"] is False
    assert "description" in " ".join(description_result["issues"]).lower()

    reordered = list(reversed(deepcopy(baseline)))
    order_result = check_catalog_parity(baseline, reordered, ["search"], ["search"])
    assert order_result["status"] == "failed"
    assert order_result["checks"]["product_ids"] is False


def test_session_creation_is_blocked_when_parity_fails(monkeypatch):
    monkeypatch.setattr(
        "app.main.get_bookstore_versions",
        lambda: {"parity_check": {"status": "failed"}},
    )
    response = client.post(
        "/api/sessions",
        json={"study_id": 1, "participant_id": "P-not-created"},
    )
    assert response.status_code == 409
    assert "parity" in response.json()["detail"].lower()

    stage_status = client.get("/api/stage-check").json()
    assert stage_status["catalogue_parity"]["status"] == "failed"
    assert stage_status["experiment_ready"] is False
