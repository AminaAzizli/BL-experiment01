from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .bookstore import get_bookstore_versions
from .config import settings
from .db import Base, SessionLocal, engine, get_db, migrate_schema
from .ground_truth import DECOYS, SEEDED_ISSUES, evaluate_seeded_issue
from .models import Participant, ResearchEvent, Session, Study
from .schemas import (
    ConsentUpdate,
    EventBatchResult,
    HealthResponse,
    ParticipantCreate,
    ParticipantRead,
    ResearchEventBatch,
    SessionComplete,
    SessionCreate,
    SessionMetrics,
    SessionResultRead,
    SessionRead,
    StudyCreate,
    StudyRead,
    TaskMetrics,
)

Base.metadata.create_all(bind=engine)
migrate_schema()

SESSION_NOT_FOUND = "Session not found"

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"message": "BehaviourLens API is running."}


@app.get("/api/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
    )


@app.get("/api/studies", response_model=list[StudyRead], tags=["studies"]) 
def list_studies(db: Session = Depends(get_db)) -> list[StudyRead]:
    studies = db.query(Study).all()
    return [StudyRead.model_validate(study) for study in studies]


@app.post("/api/studies", response_model=StudyRead, tags=["studies"]) 
def create_study(payload: StudyCreate, db: Session = Depends(get_db)) -> StudyRead:
    study_code = payload.study_code or f"ST-{uuid.uuid4().hex[:8].upper()}"

    study = Study(
        name=payload.name,
        description=payload.description,
        study_code=study_code,
        ethics_status=payload.ethics_status,
        preregistration_version=payload.preregistration_version,
        invitation_link=payload.invitation_link or "",
        default_language=payload.default_language,
    )
    db.add(study)
    db.commit()
    db.refresh(study)
    return StudyRead.model_validate(study)


@app.get("/api/studies/{study_id}/participants", response_model=list[ParticipantRead], tags=["participants"])
def list_participants_for_study(study_id: int, db: Session = Depends(get_db)) -> list[ParticipantRead]:
    participants = db.query(Participant).filter(Participant.study_id == study_id).all()
    results: list[ParticipantRead] = []
    for participant in participants:
        results.append(
            ParticipantRead(
                id=participant.id,
                study_id=participant.study_id,
                participant_id=participant.participant_id,
                recruitment_source=participant.recruitment_source,
                ui_language=participant.ui_language,
                background_questions=json.loads(participant.background_questions or "{}"),
                assigned_version=participant.assignment_version,
                assigned_persona=participant.assignment_persona,
                consent_status=participant.consent_status,
                status=participant.status,
            )
        )
    return results


@app.post("/api/studies/{study_id}/participants", response_model=ParticipantRead, tags=["participants"])
def create_participant_for_study(study_id: int, payload: ParticipantCreate, db: Session = Depends(get_db)) -> ParticipantRead:
    study = db.query(Study).filter(Study.id == study_id).first()
    if study is None:
        raise HTTPException(status_code=404, detail="Study not found")

    participant = Participant(
        study_id=study_id,
        participant_id=f"P-{uuid.uuid4().hex[:10].upper()}",
        recruitment_source=payload.recruitment_source,
        ui_language=payload.ui_language,
        background_questions=json.dumps(payload.background_questions),
        assignment_version=payload.assignment.get("version", "A"),
        assignment_persona=payload.assignment.get("persona", "baseline"),
        status="registered",
        consent_status="not_started",
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return ParticipantRead(
        id=participant.id,
        study_id=participant.study_id,
        participant_id=participant.participant_id,
        recruitment_source=participant.recruitment_source,
        ui_language=participant.ui_language,
        background_questions=json.loads(participant.background_questions or "{}"),
        assigned_version=participant.assignment_version,
        assigned_persona=participant.assignment_persona,
        consent_status=participant.consent_status,
        status=participant.status,
    )


@app.post("/api/participants/{participant_id}/consent", response_model=ParticipantRead, tags=["participants"])
def update_participant_consent(participant_id: str, payload: ConsentUpdate, db: Session = Depends(get_db)) -> ParticipantRead:
    participant = db.query(Participant).filter(Participant.participant_id == participant_id).first()
    if participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")

    participant.consent_status = payload.consent_status
    participant.status = "consented" if payload.consent_status == "consented" else participant.status
    if payload.consented_at:
        participant.consented_at = datetime.fromisoformat(payload.consented_at.isoformat())
    db.commit()
    db.refresh(participant)
    return ParticipantRead(
        id=participant.id,
        study_id=participant.study_id,
        participant_id=participant.participant_id,
        recruitment_source=participant.recruitment_source,
        ui_language=participant.ui_language,
        background_questions=json.loads(participant.background_questions or "{}"),
        assigned_version=participant.assignment_version,
        assigned_persona=participant.assignment_persona,
        consent_status=participant.consent_status,
        status=participant.status,
    )


@app.get("/api/sessions", response_model=list[SessionRead], tags=["sessions"])
def list_sessions(db: Session = Depends(get_db)) -> list[SessionRead]:
    sessions = db.query(Session).all()
    return [SessionRead.model_validate(session) for session in sessions]


@app.post("/api/sessions", response_model=SessionRead, tags=["sessions"])
def create_session(payload: SessionCreate, db: Session = Depends(get_db)) -> SessionRead:
    parity = get_bookstore_versions()["parity_check"]
    if parity["status"] != "passed":
        raise HTTPException(status_code=409, detail="Experiment session blocked: bookstore parity validation failed")

    study = db.query(Study).filter(Study.id == payload.study_id).first()
    if study is None:
        raise HTTPException(status_code=404, detail="Study not found")

    participant = db.query(Participant).filter(Participant.participant_id == payload.participant_id).first()
    if payload.actor_type == "human" and participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    if payload.actor_type == "ai" and participant is not None:
        raise HTTPException(status_code=409, detail="AI sessions must not be linked to a human participant")

    session = Session(
        session_id=f"S-{uuid.uuid4().hex[:10].upper()}",
        study_id=payload.study_id,
        participant_id=payload.participant_id,
        actor_type=payload.actor_type,
        persona=payload.persona,
        persona_parameters=json.dumps(payload.persona_parameters, separators=(",", ":")),
        model_name=payload.model_name,
        run_id=payload.run_id,
        assigned_version=payload.assigned_version,
        ui_language=payload.ui_language,
        status=payload.status,
        task_instructions=payload.task_instructions,
        task_log=payload.task_log,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionRead.model_validate(session)


@app.get("/api/participants/{participant_id}/sessions", response_model=list[SessionRead], tags=["sessions"])
def list_sessions_for_participant(participant_id: str, db: Session = Depends(get_db)) -> list[SessionRead]:
    sessions = db.query(Session).filter(Session.participant_id == participant_id).all()
    return [SessionRead.model_validate(session) for session in sessions]


@app.post("/api/sessions/{session_id}/complete", response_model=SessionRead, tags=["sessions"])
def complete_session(session_id: str, payload: SessionComplete, db: Session = Depends(get_db)) -> SessionRead:
    session = db.query(Session).filter(Session.session_id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)
    if session.status != "in_progress":
        raise HTTPException(status_code=409, detail="Session is already closed")
    session.status = payload.status
    db.commit()
    db.refresh(session)
    return SessionRead.model_validate(session)


@app.post("/api/sessions/{session_id}/events", response_model=EventBatchResult, tags=["events"])
def ingest_session_events(
    session_id: str,
    payload: ResearchEventBatch,
    db: Session = Depends(get_db),
) -> EventBatchResult:
    session = db.query(Session).filter(Session.session_id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)
    if session.status != "in_progress":
        raise HTTPException(status_code=409, detail="Session is not accepting events")

    accepted = 0
    duplicates = 0
    for event in payload.events:
        exists = (
            db.query(ResearchEvent.id)
            .filter(
                ResearchEvent.session_id == session_id,
                ResearchEvent.event_id == event.event_id,
            )
            .first()
        )
        if exists:
            duplicates += 1
            continue

        try:
            with db.begin_nested():
                db.add(
                    ResearchEvent(
                        session_id=session_id,
                        event_id=event.event_id,
                        event_type=event.event_type,
                        task_id=event.task_id,
                        occurred_at=event.occurred_at,
                        payload=json.dumps(event.payload, separators=(",", ":")),
                    )
                )
                db.flush()
            accepted += 1
        except IntegrityError:
            duplicates += 1

    db.commit()
    return EventBatchResult(accepted=accepted, duplicates=duplicates)


@app.get("/api/sessions/{session_id}/metrics", response_model=SessionMetrics, tags=["events"])
def get_session_metrics(session_id: str, db: Session = Depends(get_db)) -> SessionMetrics:
    session = db.query(Session).filter(Session.session_id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)

    events = (
        db.query(ResearchEvent)
        .filter(ResearchEvent.session_id == session_id)
        .order_by(ResearchEvent.occurred_at, ResearchEvent.id)
        .all()
    )
    event_types: dict[str, int] = {}
    task_events: dict[str, list[ResearchEvent]] = {}
    for event in events:
        event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
        if event.task_id:
            task_events.setdefault(event.task_id, []).append(event)

    task_metrics: dict[str, TaskMetrics] = {}
    for task_id, task_rows in task_events.items():
        completion_events = [row for row in task_rows if row.event_type == "task_completed"]
        completed_payloads = [json.loads(row.payload or "{}") for row in completion_events]
        success_value = next(
            (item["success"] for item in reversed(completed_payloads) if isinstance(item.get("success"), bool)),
            None,
        )
        duration = max(0, int((task_rows[-1].occurred_at - task_rows[0].occurred_at).total_seconds()))
        task_metrics[task_id] = TaskMetrics(
            event_count=len(task_rows),
            duration_seconds=duration,
            completed=bool(completion_events),
            success=success_value,
        )

    return SessionMetrics(
        session_id=session_id,
        event_count=len(events),
        event_types=event_types,
        task_metrics=task_metrics,
    )


@app.get("/api/results", response_model=list[SessionResultRead], tags=["results"])
def get_experiment_results(db: Session = Depends(get_db)) -> list[SessionResultRead]:
    sessions = db.query(Session).order_by(Session.created_at.desc()).all()
    return [_build_session_result(session, db) for session in sessions]


def _build_session_result(session: Session, db: Session) -> SessionResultRead:
    events = (
        db.query(ResearchEvent)
        .filter(ResearchEvent.session_id == session.session_id)
        .order_by(ResearchEvent.occurred_at, ResearchEvent.id)
        .all()
    )
    task_events = [event for event in events if event.task_id]
    completion = next(
        (event for event in reversed(task_events) if event.event_type in {"task_completed", "task_failed"}),
        None,
    )
    completion_payload = json.loads(completion.payload or "{}") if completion else {}
    run_metrics_event = next((event for event in reversed(events) if event.event_type == "run_metrics"), None)
    run_metrics = json.loads(run_metrics_event.payload or "{}") if run_metrics_event else {}
    started = events[0].occurred_at if events else session.created_at
    ended = events[-1].occurred_at if session.status != "in_progress" and events else None
    duration = max(0, int((ended - started).total_seconds())) if ended else None
    derived_retries = sum(event.event_type in {"task_failed", "validation_error"} for event in events)
    derived_errors = sum(event.event_type in {"validation_error", "task_failed"} for event in events)
    derived_actions = sum(
        event.event_type in {"search_submitted", "filter_changed", "add_to_cart", "quantity_changed", "checkout_started"}
        for event in events
    )
    return SessionResultRead(
        session_id=session.session_id,
        run_id=session.run_id,
        actor_type=session.actor_type,
        persona=session.persona,
        persona_parameters=json.loads(session.persona_parameters or "{}"),
        model_name=session.model_name,
        version=session.assigned_version,
        task_id=task_events[0].task_id if task_events else None,
        status=session.status,
        started_at=started,
        ended_at=ended,
        duration_seconds=duration,
        event_count=len(events),
        actions=run_metrics.get("actions", derived_actions),
        retries=run_metrics.get("retries", derived_retries),
        errors=run_metrics.get("errors", derived_errors),
        failed_attempts=sum(event.event_type == "task_failed" for event in events),
        success=run_metrics.get("success", completion_payload.get("success")),
        cart=completion_payload.get("cart", []),
    )


@app.get("/api/sessions/{session_id}/evaluation", tags=["evaluation"])
def evaluate_session_evidence(session_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    session = db.query(Session).filter(Session.session_id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)
    events = (
        db.query(ResearchEvent)
        .filter(ResearchEvent.session_id == session_id)
        .order_by(ResearchEvent.occurred_at, ResearchEvent.id)
        .all()
    )
    evidence_events = [
        {"event_type": event.event_type, "payload": json.loads(event.payload or "{}")}
        for event in events
    ]
    outcomes = {
        issue_id: evaluate_seeded_issue(issue_id, session.assigned_version, evidence_events)
        for issue_id in SEEDED_ISSUES
    }
    return {
        "session_id": session_id,
        "version": session.assigned_version,
        "tier": "Tier 1 seeded issues; observational evidence only",
        "outcomes": outcomes,
        "decoys": DECOYS,
    }


@app.get("/api/bookstore/versions", tags=["bookstore"])
def bookstore_versions() -> dict[str, Any]:
    return get_bookstore_versions()


@app.get("/api/stage-check", tags=["meta"]) 
def stage_check() -> dict[str, Any]:
    parity = get_bookstore_versions()["parity_check"]
    return {
        "foundation": "complete",
        "bookstore_shell": "complete",
        "human_flow": "complete",
        "event_collection": "complete",
        "agent_system": "implemented",
        "catalogue_parity": parity,
        "experiment_ready": parity["status"] == "passed",
        "pilot": "pending",
    }
