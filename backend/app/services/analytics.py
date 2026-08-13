from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from app.models.entities import AIEvaluation, Score, SessionStatus, TrainingSession
from app.schemas.training import (
    AbilityAnalysis,
    BusinessAbility,
    StoredTrainingReport,
    TrainingHistoryItem,
    WeaknessCategory,
)


class ReportNotFound(Exception):
    pass


class TrainingAnalyticsService:
    """Builds read models strictly from persisted rule scores and session facts."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def history(self, user_id: int) -> list[TrainingHistoryItem]:
        sessions = (
            self.db.query(TrainingSession)
            .filter(TrainingSession.user_id == user_id)
            .order_by(TrainingSession.started_at.desc(), TrainingSession.id.desc())
            .all()
        )
        return [self._history_item(session) for session in sessions]

    def report(self, session: TrainingSession) -> StoredTrainingReport:
        if session.status != SessionStatus.completed.value or session.completed_at is None:
            raise ReportNotFound("Final report is available only for completed sessions")
        score = self._final_score(session.id)
        if score is None:
            raise ReportNotFound("Final score not found")
        evaluation = (
            self.db.query(AIEvaluation)
            .filter(AIEvaluation.session_id == session.id, AIEvaluation.agent_name == "examiner")
            .order_by(AIEvaluation.id.desc())
            .first()
        )
        details = score.details or {}
        return StoredTrainingReport(
            session_id=session.id,
            user_id=session.user_id,
            scenario_id=session.scenario_id,
            scenario_title=session.scenario.title,
            business_type=session.scenario.business_type,
            difficulty=session.scenario.difficulty,
            status=session.status,
            started_at=session.started_at.isoformat(),
            completed_at=session.completed_at.isoformat(),
            passed=self._is_passed(score),
            rule_score=score.rule_score,
            total_score=score.total_score,
            missing_steps=list(details.get("missing_steps", [])),
            violations=list(details.get("violations", [])),
            suggestions=list(details.get("suggestions", [])),
            examiner_report=(evaluation.result or {}).get("content", "暂无考官评价解释。") if evaluation else "暂无考官评价解释。",
        )

    def abilities(self, user_id: int) -> AbilityAnalysis:
        sessions = (
            self.db.query(TrainingSession)
            .filter(
                TrainingSession.user_id == user_id,
                TrainingSession.status == SessionStatus.completed.value,
            )
            .order_by(TrainingSession.id)
            .all()
        )
        grouped: dict[str, list[tuple[TrainingSession, Score]]] = defaultdict(list)
        weakness_counter: Counter[str] = Counter()
        scored_sessions: list[tuple[TrainingSession, Score]] = []

        for session in sessions:
            score = self._final_score(session.id)
            if score is None:
                continue
            scored_sessions.append((session, score))
            grouped[session.scenario.business_type].append((session, score))
            details = score.details or {}
            weakness_counter.update(f"缺失步骤：{step}" for step in details.get("missing_steps", []))
            weakness_counter.update(f"规则违规：{violation}" for violation in details.get("violations", []))

        abilities = []
        for business_type, records in sorted(grouped.items()):
            scores = [score.total_score for _, score in records]
            passed_count = sum(self._is_passed(score) for _, score in records)
            average = round(sum(scores) / len(scores), 2)
            abilities.append(
                BusinessAbility(
                    business_type=business_type,
                    scenario_title=records[-1][0].scenario.title,
                    completed_count=len(records),
                    average_score=average,
                    pass_rate=round(passed_count / len(records) * 100, 2),
                    level=self._ability_level(average),
                )
            )

        overall_scores = [score.total_score for _, score in scored_sessions]
        passed_total = sum(self._is_passed(score) for _, score in scored_sessions)
        recommendations = [
            ability.business_type
            for ability in sorted(abilities, key=lambda item: (item.average_score, item.business_type))
            if ability.average_score < 85
        ][:3]
        return AbilityAnalysis(
            user_id=user_id,
            completed_sessions=len(scored_sessions),
            average_score=round(sum(overall_scores) / len(overall_scores), 2) if overall_scores else 0,
            pass_rate=round(passed_total / len(scored_sessions) * 100, 2) if scored_sessions else 0,
            business_abilities=abilities,
            weaknesses=[
                WeaknessCategory(category=category, count=count)
                for category, count in weakness_counter.most_common(5)
            ],
            recommended_business_types=recommendations,
        )

    def _history_item(self, session: TrainingSession) -> TrainingHistoryItem:
        score = self._final_score(session.id) if session.status == SessionStatus.completed.value else None
        return TrainingHistoryItem(
            session_id=session.id,
            scenario_id=session.scenario_id,
            scenario_title=session.scenario.title,
            business_type=session.scenario.business_type,
            difficulty=session.scenario.difficulty,
            status=session.status,
            started_at=session.started_at.isoformat(),
            completed_at=session.completed_at.isoformat() if session.completed_at else None,
            total_score=score.total_score if score else None,
            rule_score=score.rule_score if score else None,
            passed=self._is_passed(score) if score else None,
        )

    def _final_score(self, session_id: int) -> Score | None:
        return (
            self.db.query(Score)
            .filter(Score.session_id == session_id)
            .order_by(Score.id.desc())
            .first()
        )

    @staticmethod
    def _is_passed(score: Score) -> bool:
        details = score.details or {}
        return score.rule_score >= 60 and not details.get("missing_steps") and not details.get("violations")

    @staticmethod
    def _ability_level(average_score: float) -> str:
        if average_score >= 90:
            return "proficient"
        if average_score >= 75:
            return "competent"
        if average_score >= 60:
            return "developing"
        return "needs_practice"
