from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from .db import Base


class Study(Base):
    __tablename__ = "studies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    study_code = Column(String(64), unique=True, index=True, nullable=False, default="study")
    ethics_status = Column(String(64), default="not_obtained")
    preregistration_version = Column(String(64), default="v0")
    invitation_link = Column(Text, default="")
    default_language = Column(String(8), default="en")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    study_id = Column(Integer, nullable=False)
    participant_id = Column(String(64), unique=True, index=True, nullable=False)
    recruitment_source = Column(String(128), default="unknown")
    ui_language = Column(String(8), default="en")
    background_questions = Column(Text, default="{}")
    consent_status = Column(String(32), default="not_started")
    consented_at = Column(DateTime(timezone=True), nullable=True)
    assignment_version = Column(String(8), default="A")
    assignment_persona = Column(String(64), default="baseline")
    status = Column(String(32), default="registered")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    participant_id = Column(String(64), nullable=False)
    study_id = Column(Integer, nullable=False)
    actor_type = Column(String(16), default="human", server_default="human", nullable=False)
    persona = Column(String(64), default="human_participant", server_default="human_participant", nullable=False)
    persona_parameters = Column(Text, default="{}", server_default="{}", nullable=False)
    model_name = Column(String(128), nullable=True)
    run_id = Column(String(64), nullable=True, index=True)
    assigned_version = Column(String(8), default="A")
    ui_language = Column(String(8), default="en")
    status = Column(String(32), default="in_progress")
    task_instructions = Column(Text, default="")
    task_log = Column(Text, default="")
    seq_score = Column(Integer, nullable=True)
    sus_score = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ResearchEvent(Base):
    __tablename__ = "research_events"
    __table_args__ = (UniqueConstraint("session_id", "event_id", name="uq_event_session_event_id"),)

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), index=True, nullable=False)
    event_id = Column(String(128), nullable=False)
    event_type = Column(String(96), index=True, nullable=False)
    task_id = Column(String(32), index=True, nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    payload = Column(Text, default="{}", nullable=False)
