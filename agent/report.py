from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


RESEARCH_QUESTION = "Do adjustable AI persona parameters produce stable, measurable behavioural differences, and do those differences correspond to genuine human usability friction?"


def _flatten(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": result.get("run_id", ""),
        "session_id": result.get("session_id", ""),
        "actor_type": result.get("actor_type", "ai"),
        "model_name": result.get("model_name", ""),
        "persona": result.get("persona", ""),
        "persona_parameters": json.dumps(result.get("persona_parameters", {}), ensure_ascii=True),
        "version": result.get("version", ""),
        "task_id": result.get("task_id", ""),
        "status": result.get("status", ""),
        "success": result.get("success"),
        "started_at": result.get("started_at", ""),
        "ended_at": result.get("ended_at", ""),
        "duration_seconds": result.get("duration_seconds", 0),
        "actions": result.get("actions", 0),
        "retries": result.get("retries", 0),
        "errors": result.get("errors", 0),
        "failed_attempts": result.get("failed_attempts", 0),
        "event_count": result.get("event_count", 0),
        "subtotal": result.get("subtotal", 0),
        "cart": json.dumps(result.get("cart", []), ensure_ascii=True),
        "error_message": result.get("error_message", ""),
    }


def _fetch_sessions(api_base_url: str) -> list[dict[str, Any]]:
    try:
        response = requests.get(f"{api_base_url.rstrip('/')}/api/results", timeout=10)
        response.raise_for_status()
        sessions = response.json()
        return sessions if isinstance(sessions, list) else []
    except requests.RequestException:
        return []


def _merge_run_history(results_path: Path, new_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        previous = json.loads(results_path.read_text(encoding="utf-8")).get("runs", [])
        if not isinstance(previous, list):
            previous = []
    except (OSError, json.JSONDecodeError):
        previous = []

    runs_by_id = {
        str(run["run_id"]): run
        for run in previous
        if isinstance(run, dict) and run.get("run_id")
    }
    for run in new_runs:
        if run.get("run_id"):
            runs_by_id[str(run["run_id"])] = {**runs_by_id.get(str(run["run_id"]), {}), **run}
    return list(runs_by_id.values())


def _group_records(records: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], ...]:
    actor_groups: dict[str, list[dict[str, Any]]] = {}
    version_groups: dict[str, list[dict[str, Any]]] = {}
    persona_groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        actor_groups.setdefault(str(record.get("actor_type", "unknown")), []).append(record)
        version_groups.setdefault(str(record.get("version", "unknown")), []).append(record)
        if record.get("actor_type") == "ai":
            condition = f"{record.get('version', 'unknown')}/{record.get('task_id', 'unknown')}"
            persona_key = f"{record.get('persona', 'unknown')} ({condition})"
            persona_groups.setdefault(persona_key, []).append(record)
    return actor_groups, version_groups, persona_groups


def _actor_summary(actor: str, group: list[dict[str, Any]]) -> str:
    outcomes = [record["success"] for record in group if record.get("success") is not None]
    return (
        f"- {actor}: {sum(outcomes)}/{len(outcomes)} verified successes among {len(outcomes)} sessions "
        f"with a verified outcome; {len(group) - len(outcomes)} without a verified task outcome."
    )


def _version_summary(version: str, group: list[dict[str, Any]]) -> str:
    outcomes = [record["success"] for record in group if record.get("success") is not None]
    durations = [float(record["duration_seconds"]) for record in group if record.get("duration_seconds") is not None]
    outcome_text = f"{sum(outcomes)}/{len(outcomes)} verified successes" if outcomes else "no verified task outcomes"
    duration_text = f"mean duration {sum(durations) / len(durations):.2f}s" if durations else "duration unavailable"
    return f"- Version {version}: {outcome_text}; {duration_text}."


def _persona_summary(persona: str, group: list[dict[str, Any]]) -> str:
    outcomes = [record["success"] for record in group if record.get("success") is not None]
    action_counts = [int(record["actions"]) for record in group if record.get("actions") is not None]
    outcome_text = (
        f"{sum(outcomes)}/{len(outcomes)} verified successes among {len(outcomes)} verified outcomes"
        if outcomes
        else "no verified task outcomes"
    )
    actions_text = f"mean actions {sum(action_counts) / len(action_counts):.1f}" if action_counts else "actions unavailable"
    return f"- {persona}: {outcome_text}; {actions_text}; {len(group)} recorded runs."


def write_reports(api_base_url: str, runs: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "mini_experiment_results.json"
    csv_path = output_dir / "mini_experiment_results.csv"
    summary_path = output_dir / "mini_experiment_summary.md"

    all_sessions = _fetch_sessions(api_base_url)
    run_history = _merge_run_history(results_path, runs)
    records_by_session = {
        str(session["session_id"]): session
        for session in all_sessions
        if session.get("session_id")
    }
    for run in run_history:
        session_id = run.get("session_id")
        if session_id:
            records_by_session[str(session_id)] = {
                **records_by_session.get(str(session_id), {}),
                **run,
            }
    comparison_records = list(records_by_session.values())
    results_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "runs": run_history,
                "sessions": all_sessions,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    rows = [_flatten(record) for record in comparison_records]
    fieldnames = list(rows[0]) if rows else list(_flatten({}))
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    verified_invocation = [run["success"] for run in runs if run.get("success") is not None]
    successful = sum(bool(outcome) for outcome in verified_invocation)
    actor_groups, version_groups, persona_groups = _group_records(comparison_records)
    actor_lines = [_actor_summary(actor, group) for actor, group in sorted(actor_groups.items())]
    version_lines = [_version_summary(version, group) for version, group in sorted(version_groups.items())]
    persona_lines = [_persona_summary(persona, group) for persona, group in sorted(persona_groups.items())]
    ai_records = [record for record in comparison_records if record.get("actor_type") == "ai"]
    summary = [
        "# BehaviourLens Mini-Experiment Summary",
        "",
        "**Preliminary demonstration results. These observations are not statistically significant evidence.**",
        "",
        "## Research question",
        RESEARCH_QUESTION,
        "",
        "## Experimental setup",
        "- One shared book catalogue is used for both A and B; only interface features differ.",
        "- Version A seeds S1, S3, S7, S8, and S10; Version B improves those same features.",
        "- AI runs use a fresh Chromium context and a fresh backend session per repetition.",
        "- Task outcome is checked against the rendered cart, independently of model claims.",
        "- Interaction events are collected from the actual browser UI and backend API.",
        "",
        "## Tasks and persona definitions",
        "- T1: find Signal in the Dust and add it to the cart.",
        "- T5: change the preloaded cart item's quantity from one to two and verify the subtotal.",
        "- Persona parameter definitions are stored in agent/personas.py and included with each run.",
        f"- Model(s): {', '.join(sorted({str(record.get('model_name', 'unknown')) for record in ai_records})) or 'none (no AI runs)'}.",
        "",
        "## Results",
        f"- AI runs in this invocation: {len(runs)}",
        f"- AI sessions in stored results: {len(ai_records)}",
        f"- Verified task successes: {successful}",
        (
            f"- Verified task success rate for this invocation: {successful / len(verified_invocation):.1%} "
            f"({successful}/{len(verified_invocation)} verified outcomes)."
            if verified_invocation
            else "- Verified task success rate for this invocation: not available"
        ),
        "- Human/AI actor comparison:",
        *actor_lines,
        "- Version comparisons:",
        *version_lines,
        "- Persona comparisons across all stored AI sessions, grouped by version/task condition:",
        *persona_lines,
        "- See the CSV/JSON exports for version, persona, task, duration, actions, retries, errors, and final cart state.",
        "",
        "## Limitations and interpretation",
        "- Small local demonstrations are descriptive only; no significance testing is claimed.",
        "- Human comparison rows appear only when real human sessions have been recorded; no sample data is generated.",
        "- Behavioural indicators such as retries are observations and do not prove a participant's mental state.",
        "- Seeded issue detection and human validation are not yet a full evaluation pipeline.",
        "",
    ]
    summary_path.write_text("\n".join(summary), encoding="utf-8")
    return [summary_path, csv_path, results_path]
