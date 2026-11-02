from app.ground_truth import DECOYS, SEEDED_ISSUES, evaluate_seeded_issue


def test_seeded_issue_evaluation_detects_observable_evidence_and_abstains_without_it():
    assert set(SEEDED_ISSUES) == {"S1", "S3", "S7", "S8", "S10"}
    assert "S5" not in SEEDED_ISSUES
    assert DECOYS
    no_evidence = evaluate_seeded_issue("S8", "A", [])
    assert no_evidence["outcome"] == "insufficient_evidence"

    evidence = evaluate_seeded_issue(
        "S8",
        "A",
        [{"event_type": "quantity_changed", "payload": {"requires_confirmation": True}}],
    )
    assert evidence["outcome"] == "detected"
    assert "not proof" in evidence["reason"]

    no_friction = evaluate_seeded_issue(
        "S8",
        "A",
        [{"event_type": "quantity_changed", "payload": {"requires_confirmation": False}}],
    )
    assert no_friction["outcome"] == "not_detected"

    version_b = evaluate_seeded_issue("S8", "B", [{"event_type": "cart_updated"}])
    assert version_b["outcome"] == "insufficient_evidence"
