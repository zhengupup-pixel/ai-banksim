from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.entities import Scenario, User, UserRole
from app.schemas.training import AbilityAnalysis, BusinessAbility
from app.services.analytics import TrainingAnalyticsService
from app.services.demo_scenarios import DEMO_SCENARIOS
from app.services.planning import TrainingPlanService


def test_new_student_plan_prioritizes_untrained_basic_scenarios() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(
            username="new_student", display_name="New Student", role=UserRole.student.value,
            password_hash="disabled", is_active=True,
        )
        db.add(user)
        db.add_all(Scenario(**item) for item in DEMO_SCENARIOS)
        db.commit()

        service = TrainingPlanService(db)
        analysis = TrainingAnalyticsService(db).abilities(user.id)
        items = service._select_items(analysis, db.query(Scenario).order_by(Scenario.id).all())

        assert [item.business_type for item in items] == ["account_opening", "deposit", "loss_reporting"]
        assert all(item.source == "untrained_business" for item in items)
        assert all(item.target_score == 85 for item in items)
    engine.dispose()


def test_weak_trained_business_precedes_untrained_scenarios() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(Scenario(**item) for item in DEMO_SCENARIOS)
        db.commit()
        analysis = AbilityAnalysis(
            user_id=1, completed_sessions=2, average_score=55, pass_rate=0,
            business_abilities=[
                BusinessAbility(
                    business_type="transfer", scenario_title="个人账户转账",
                    completed_count=2, average_score=55, pass_rate=0, level="needs_practice",
                )
            ],
            weaknesses=[], recommended_business_types=["transfer"],
        )

        items = TrainingPlanService(db)._select_items(
            analysis, db.query(Scenario).order_by(Scenario.id).all()
        )

        assert items[0].business_type == "transfer"
        assert items[0].source == "weak_business"
        assert items[0].target_score == 85
        assert all(item.business_type != "transfer" for item in items[1:])
    engine.dispose()
