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
        "success": result.get("success"),
        "started_at": result.get("started_at", ""),
        "ended_at": result.get("ended_at", ""),
        "duration_seconds": result.get("duration_seconds", 0),
        "actions": result.get("actions", 0),
        "retries": result.get("retries", 0),
        "errors": result.get("errors", 0),
        "failed_attempts": result.get("failed_attempts", 0),
        "subtotal": result.get("subtotal", 0),
        "cart": json.dumps(result.get("cart", []), ensure_ascii=True),
        "error_message": result.get("error_message", ""),
    }


def write_reports(api_base_url: str, runs: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "mini_experiment_results.json"
    csv_path = output_dir / "mini_experiment_results.csv"
    summary_path = output_dir / "mini_experiment_summary.md"

    try:
        response = requests.get(f"{api_base_url.rstrip('/')}/api/results", timeout=10)
        response.raise_for_status()
        all_sessions = response.json()
    except requests.RequestException:
        all_sessions = []

    results_path.write_text(
        json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "runs": runs, "sessions": all_sessions}, indent=2),
        encoding="utf-8",
    )
    ai_session_ids = {item.get("session_id") for item in runs}
    human_sessions = [
        item
        for item in all_sessions
        if item.get("actor_type") == "human" and item.get("session_id") not in ai_session_ids
    ]
    rows = [_flatten(item) for item in runs]
    rows.extend(_flatten(item) for item in human_sessions)
    fieldnames = list(rows[0]) if rows else list(_flatten({}))
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    successful = sum(bool(run.get("success")) for run in runs)
    comparison_records = [*runs, *human_sessions]
    actor_groups: dict[str, list[dict[str, Any]]] = {}
    version_groups: dict[str, list[dict[str, Any]]] = {}
    persona_groups: dict[str, list[dict[str, Any]]] = {}
    for record in comparison_records:
        actor_groups.setdefault(str(record.get("actor_type", "unknown")), []).append(record)
        version_groups.setdefault(str(record.get("version", "unknown")), []).append(record)
    for run in runs:
        persona_groups.setdefault(str(run.get("persona", "unknown")), []).append(run)
    actor_lines = []
    for actor, group in sorted(actor_groups.items()):
        outcomes = [record.get("success") for record in group if record.get("success") is not None]
        actor_lines.append(
            f"- {actor}: {sum(outcomes)}/{len(outcomes)} verified successes among {len(outcomes)} sessions with a verified outcome; {len(group) - len(outcomes)} without a verified task outcome."
        )
    version_lines = []
    for version, group in sorted(version_groups.items()):
        outcomes = [record.get("success") for record in group if record.get("success") is not None]
        durations = [float(record["duration_seconds"]) for record in group if record.get("duration_seconds") is not None]
        outcome_summary = f"{sum(outcomes)}/{len(outcomes)} verified successes" if outcomes else "no verified task outcomes"
        duration_summary = f"mean duration {sum(durations) / len(durations):.2f}s" if durations else "duration unavailable"
        version_lines.append(f"- Version {version}: {outcome_summary}; {duration_summary}.")
    persona_lines = [
        f"- {persona}: {sum(bool(run.get('success')) for run in group)}/{len(group)} verified successes; mean actions {sum(int(run.get('actions', 0)) for run in group) / len(group):.1f}."
        for persona, group in sorted(persona_groups.items())
    ]
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
        f"- Model(s): {', '.join(sorted({str(run.get('model_name', 'unknown')) for run in runs})) or 'none (no AI runs)'}.",
        "",
        "## Results",
        f"- AI runs in this invocation: {len(runs)}",
        f"- Verified task successes: {successful}",
        f"- Verified task success rate for this invocation: {successful / len(runs):.1%}" if runs else "- Verified task success rate for this invocation: not available",
        "- Human/AI actor comparison:",
        *actor_lines,
        "- Version comparisons:",
        *version_lines,
        "- Persona comparisons:",
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
