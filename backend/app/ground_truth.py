from __future__ import annotations

from typing import Any

SEEDED_ISSUES: dict[str, dict[str, str]] = {
    "S1": {"name": "Vague filter label", "evidence_event": "filter_changed"},
    "S3": {"name": "Unclear validation guidance", "evidence_event": "validation_error"},
    "S7": {"name": "Low-contrast add-to-cart control", "evidence_event": "add_to_cart"},
    "S8": {"name": "Hidden quantity update step", "evidence_event": "quantity_changed"},
    "S10": {"name": "Unclear checkout action label", "evidence_event": "checkout_started"},
}

DECOYS = [
    "Search box",
    "Product card layout",
    "Price display",
    "Breadcrumb navigation",
    "Cart remove button",
    "Name and contact field labels",
    "Pagination controls",
]


def evaluate_seeded_issue(issue_id: str, version: str, events: list[dict[str, Any]]) -> dict[str, str]:
    issue = SEEDED_ISSUES.get(issue_id)
    if issue is None:
        return {"outcome": "insufficient_evidence", "reason": "Unknown seeded issue."}
    if version != "A":
        return {"outcome": "insufficient_evidence", "reason": "Issue is seeded only in Version A."}

    attempts = [event for event in events if event.get("event_type") == issue["evidence_event"]]
    evidence = attempts
    if issue_id == "S1":
        evidence = [event for event in evidence if event.get("payload", {}).get("filter_label") == "Refine"]
    elif issue_id == "S7":
        evidence = [event for event in evidence if event.get("payload", {}).get("low_contrast") is True]
    elif issue_id == "S8":
        evidence = [event for event in evidence if event.get("payload", {}).get("requires_confirmation") is True]
    elif issue_id == "S10":
        evidence = [
            event for event in evidence
            if event.get("payload", {}).get("button_label") == "Continue"
        ]
    if not evidence:
        if attempts:
            return {
                "outcome": "not_detected",
                "reason": f"The relevant interaction was observed, but it did not show the seeded behavior for {issue['name']}.",
            }
        return {"outcome": "insufficient_evidence", "reason": "No relevant interaction event was recorded."}
    return {
        "outcome": "detected",
        "reason": f"Relevant observable interaction recorded for {issue['name']}; this is evidence, not proof of subjective frustration.",
    }
