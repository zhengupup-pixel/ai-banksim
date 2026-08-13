from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.entities import Scenario, Score, SessionStatus, TrainingAction, TrainingSession, User
from app.schemas.training import TrainingActionCreate, TrainingSessionCreate
from app.services.rule_engine import BusinessRuleEngine, RuleCheck
from app.services.scoring import ScoringEngine


class TrainingServiceError(Exception):
    """Base error raised by the deterministic training workflow."""


class TrainingResourceNotFound(TrainingServiceError):
    pass


class InvalidTrainingState(TrainingServiceError):
    pass


class TrainingService:
    """Owns session state changes; API routes only translate HTTP input/output."""

    def __init__(
        self,
        db: Session,
        rule_engine: BusinessRuleEngine | None = None,
        scoring_engine: ScoringEngine | None = None,
    ) -> None:
        self.db = db
        self.rule_engine = rule_engine or BusinessRuleEngine()
        self.scoring_engine = scoring_engine or ScoringEngine()

    def create_session(self, payload: TrainingSessionCreate, user: User) -> TrainingSession:
        if self.db.get(Scenario, payload.scenario_id) is None:
            raise TrainingResourceNotFound("Scenario not found")

        session = TrainingSession(
            user_id=user.id,
            scenario_id=payload.scenario_id,
            context={"performed_steps": []},
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def submit_action(self, session_id: int, payload: TrainingActionCreate) -> RuleCheck:
        session = self._get_session(session_id)
        self._require_active(session)

        self.db.add(TrainingAction(session_id=session_id, action_type=payload.action_type, payload=payload.payload))

        performed_steps = list(session.context.get("performed_steps", []))
        if payload.action_type not in performed_steps:
            performed_steps.append(payload.action_type)
        session.context = {**session.context, **payload.payload, "performed_steps": performed_steps}

        rule_check = self._evaluate(session)
        self._save_score(session, rule_check)
        self.db.commit()
        return rule_check

    def complete_session(self, session_id: int) -> tuple[TrainingSession, RuleCheck, Score]:
        session = self._get_session(session_id)
        self._require_active(session)

        rule_check = self._evaluate(session)
        score = self._save_score(session, rule_check)
        session.status = SessionStatus.completed.value
        session.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()
        self.db.refresh(session)
        self.db.refresh(score)
        return session, rule_check, score

    def _get_session(self, session_id: int) -> TrainingSession:
        session = self.db.get(TrainingSession, session_id)
        if session is None:
            raise TrainingResourceNotFound("Training session not found")
        return session

    @staticmethod
    def _require_active(session: TrainingSession) -> None:
        if session.status != SessionStatus.active.value:
            raise InvalidTrainingState("Only active training sessions can be changed")

    def _evaluate(self, session: TrainingSession) -> RuleCheck:
        performed_steps = list(session.context.get("performed_steps", []))
        return self.rule_engine.evaluate(
            session.scenario.expected_steps,
            performed_steps,
            session.context,
            session.scenario.rule_policy,
        )

    def _save_score(self, session: TrainingSession, rule_check: RuleCheck) -> Score:
        score = Score(
            session_id=session.id,
            **self.scoring_engine.calculate_total(rule_check, scoring_policy=session.scenario.scoring_policy),
        )
        self.db.add(score)
        return score
