from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    """Return naive UTC for current SQLite columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UserRole(str, Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class SessionStatus(str, Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32), default=UserRole.student.value)
    password_hash: Mapped[str] = mapped_column(String(256))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    sessions: Mapped[list["TrainingSession"]] = relationship(back_populates="user")
    auth_tokens: Mapped[list["AuthToken"]] = relationship(back_populates="user")


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    user: Mapped[User] = relationship(back_populates="auth_tokens")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(128), index=True)
    id_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    risk_level: Mapped[str] = mapped_column(String(32), default="normal")
    profile: Mapped[dict] = mapped_column(JSON, default=dict)

    memories: Mapped[list["CustomerMemory"]] = relationship(back_populates="customer")


class CustomerMemory(Base):
    __tablename__ = "customer_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    memory_type: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    customer: Mapped[Customer] = relationship(back_populates="memories")


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160), index=True)
    business_type: Mapped[str] = mapped_column(String(64), index=True)
    difficulty: Mapped[str] = mapped_column(String(32), default="basic")
    description: Mapped[str] = mapped_column(Text)
    expected_steps: Mapped[list[str]] = mapped_column(JSON, default=list)
    risk_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    scoring_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    rule_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    customer_profile: Mapped[dict] = mapped_column(JSON, default=dict)

    sessions: Mapped[list["TrainingSession"]] = relationship(back_populates="scenario")
    versions: Mapped[list["ScenarioVersion"]] = relationship(back_populates="scenario")


class ScenarioVersion(Base):
    __tablename__ = "scenario_versions"
    __table_args__ = (
        UniqueConstraint("scenario_id", "version_number", name="uq_scenario_version_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    changed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    scenario: Mapped[Scenario] = relationship(back_populates="versions")


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"))
    status: Mapped[str] = mapped_column(String(32), default=SessionStatus.active.value)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="sessions")
    scenario: Mapped[Scenario] = relationship(back_populates="sessions")
    actions: Mapped[list["TrainingAction"]] = relationship(back_populates="session")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="session")
    scores: Mapped[list["Score"]] = relationship(back_populates="session")
    ai_evaluations: Mapped[list["AIEvaluation"]] = relationship(back_populates="session")


class TrainingAction(Base):
    __tablename__ = "training_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"))
    action_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    session: Mapped[TrainingSession] = relationship(back_populates="actions")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"))
    speaker: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    session: Mapped[TrainingSession] = relationship(back_populates="conversations")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"))
    total_score: Mapped[float] = mapped_column(Float)
    rule_score: Mapped[float] = mapped_column(Float)
    ai_score: Mapped[float] = mapped_column(Float, default=0)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    session: Mapped[TrainingSession] = relationship(back_populates="scores")


class AIEvaluation(Base):
    __tablename__ = "ai_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"))
    agent_name: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    session: Mapped[TrainingSession] = relationship(back_populates="ai_evaluations")


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(160))
    goals: Mapped[list[str]] = mapped_column(JSON, default=list)
    schedule: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="plan")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("training_plans.id"), nullable=True, index=True)
    recommendation_type: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    plan: Mapped[TrainingPlan | None] = relationship(back_populates="recommendations")
