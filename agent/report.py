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


def _public_aggregate(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = {}
    for session in sessions:
        condition = (
            str(session.get("actor_type", "unknown")),
            str(session.get("version", "unknown")),
            str(session.get("task_id") or "unknown"),
            str(session.get("persona", "unknown")),
            str(session.get("model_name") or "unknown"),
        )
        grouped.setdefault(condition, []).append(session)

    rows: list[dict[str, Any]] = []
    for condition, records in sorted(grouped.items()):
        actor_type, version, task_id, persona, model_name = condition
        outcomes = [record["success"] for record in records if record.get("success") is not None]
        durations = [float(record["duration_seconds"]) for record in records if record.get("duration_seconds") is not None]
        action_counts = [int(record.get("actions", 0)) for record in records]
        retries = [int(record.get("retries", 0)) for record in records]
        errors = [int(record.get("errors", 0)) for record in records]
        rows.append(
            {
                "actor_type": actor_type,
                "version": version,
                "task_id": task_id,
                "persona": persona,
                "model_name": model_name,
                "session_count": len(records),
                "verified_outcomes": len(outcomes),
                "successes": sum(bool(outcome) for outcome in outcomes),
                "success_rate": round(sum(bool(outcome) for outcome in outcomes) / len(outcomes), 4) if outcomes else None,
                "unverified_outcomes": len(records) - len(outcomes),
                "mean_duration_seconds": round(sum(durations) / len(durations), 2) if durations else None,
                "mean_actions": round(sum(action_counts) / len(action_counts), 2) if action_counts else None,
                "mean_retries": round(sum(retries) / len(retries), 2) if retries else None,
                "mean_errors": round(sum(errors) / len(errors), 2) if errors else None,
            }
        )
    return rows


def _write_public_snapshot(sessions: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    public_dir = output_dir / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    summary_path = public_dir / "mini_experiment_summary.md"
    csv_path = public_dir / "mini_experiment_results.csv"
    json_path = public_dir / "mini_experiment_results.json"
    rows = _public_aggregate(sessions)
    public_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification": "preliminary aggregate demonstration data",
        "research_question": RESEARCH_QUESTION,
        "sessions_included": len(sessions),
        "conditions": rows,
    }
    json_path.write_text(json.dumps(public_data, indent=2), encoding="utf-8")
    columns = list(rows[0]) if rows else [
        "actor_type", "version", "task_id", "persona", "model_name", "session_count",
        "verified_outcomes", "successes", "success_rate", "unverified_outcomes",
        "mean_duration_seconds", "mean_actions", "mean_retries", "mean_errors",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    summary = [
        "# BehaviourLens Mini-Experiment Summary",
        "",
        "**Preliminary aggregate demonstration results. These observations are not statistically significant evidence.**",
        "",
        "## Research question",
        RESEARCH_QUESTION,
        "",
        "## Experimental setup",
        "- A and B use the same validated, ordered product catalogue and actions.",
        "- A includes S1, S3, S7, S8, and S10; B improves those interface details.",
        "- Completed mini-experiment tasks are T1 product discovery and T5 cart editing.",
        "- AI outcomes are verified from the rendered cart; unverified attempts are reported separately.",
        "- Persona summaries are grouped by actor, version, task, persona, and model.",
        "",
        "## Aggregate results",
        f"- Recorded sessions included: {len(sessions)}",
        "- Each line reports sample counts, verified success rate, and mean behavioral measures for that condition.",
        "",
        "## Condition comparisons",
        *[
            f"- {row['actor_type']} | {row['version']} | {row['task_id']} | {row['persona']} | {row['model_name']}: "
            f"{row['successes']}/{row['verified_outcomes']} verified successes; "
            f"{row['unverified_outcomes']} unverified; mean actions {row['mean_actions']}; "
            f"mean duration {row['mean_duration_seconds']}s; mean retries {row['mean_retries']}."
            for row in rows
        ],
        "",
        "## Limitations",
        "- These are small, local demonstration samples; no statistical-significance claim is made.",
        "- Behavioral indicators do not establish subjective frustration or usability causality.",
        "- Aggregates omit session identifiers, run IDs, event payloads, timestamps, screenshots, and model transcripts.",
        "",
    ]
    summary_path.write_text("\n".join(summary), encoding="utf-8")
    return [summary_path, csv_path, json_path]


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

    _write_public_snapshot(comparison_records, output_dir)

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
