from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.orchestrator import AgentOrchestrator
from app.api.dependencies import get_auth_context, get_current_user, require_roles
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import AIEvaluation, AuthToken, Scenario, ScenarioVersion, TrainingSession, User, UserRole
from app.schemas.auth import LoginRequest, LoginResponse, UserRead
from app.schemas.conversation import ConversationMessageRead, CustomerMessageCreate, CustomerMessageResponse
from app.schemas.planning import TrainingPlanRead
from app.schemas.training import (
    AIEvaluationRequest,
    AIEvaluationResponse,
    AbilityAnalysis,
    FinalTrainingReport,
    RuleCheckResult,
    ScenarioRead,
    ScenarioUpdate,
    ScenarioVersionRead,
    StoredTrainingReport,
    TrainingActionCreate,
    TrainingHistoryItem,
    TrainingSessionCreate,
    TrainingSessionRead,
)
from app.services.training import InvalidTrainingState, TrainingResourceNotFound, TrainingService
from app.db.seed_demo import seed_demo_data as seed_demo_records
from app.services.auth import AuthenticationError, AuthService
from app.services.analytics import ReportNotFound, TrainingAnalyticsService
from app.services.conversation import ConversationService
from app.services.planning import TrainingPlanService

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ai-banksim-api"}


@router.post("/dev/seed")
def seed_demo_data(db: Session = Depends(get_db)) -> dict:
    if not get_settings().enable_dev_seed:
        raise HTTPException(status_code=404, detail="Not found")
    seed_demo_records(db)
    return {"seeded": True}


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    service = AuthService(db)
    try:
        user = service.authenticate(payload.username, payload.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc
    token, expires_at = service.issue_token(user)
    return LoginResponse(access_token=token, expires_at=expires_at.isoformat(), user=UserRead.model_validate(user))


@router.get("/auth/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/auth/logout", status_code=204)
def logout(
    context: tuple[AuthToken, User] = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> None:
    AuthService(db).revoke(context[0])


@router.get("/scenarios", response_model=list[ScenarioRead])
def list_scenarios(
    _: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Scenario]:
    return db.query(Scenario).order_by(Scenario.id).all()


@router.put("/scenarios/{scenario_id}", response_model=ScenarioRead)
def update_scenario(
    scenario_id: int,
    payload: ScenarioUpdate,
    editor: User = Depends(require_roles(UserRole.teacher.value, UserRole.admin.value)),
    db: Session = Depends(get_db),
) -> Scenario:
    scenario = db.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    previous = scenario_snapshot(scenario)
    current_version = (
        db.query(func.max(ScenarioVersion.version_number))
        .filter(ScenarioVersion.scenario_id == scenario_id)
        .scalar()
        or 0
    )
    db.add(
        ScenarioVersion(
            scenario_id=scenario_id,
            version_number=current_version + 1,
            changed_by_user_id=editor.id,
            snapshot=previous,
        )
    )
    values = payload.model_dump(mode="json")
    public_profile = values.pop("customer_profile")
    values["customer_profile"] = {
        **public_profile,
        "internal_notes": (scenario.customer_profile or {}).get("internal_notes", []),
    }
    for field, value in values.items():
        setattr(scenario, field, value)
    db.commit()
    db.refresh(scenario)
    return scenario


@router.get("/scenarios/{scenario_id}/versions", response_model=list[ScenarioVersionRead])
def list_scenario_versions(
    scenario_id: int,
    _: User = Depends(require_roles(UserRole.teacher.value, UserRole.admin.value)),
    db: Session = Depends(get_db),
) -> list[ScenarioVersionRead]:
    if db.get(Scenario, scenario_id) is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    versions = (
        db.query(ScenarioVersion)
        .filter(ScenarioVersion.scenario_id == scenario_id)
        .order_by(ScenarioVersion.version_number.desc())
        .all()
    )
    return [
        ScenarioVersionRead(
            id=item.id,
            scenario_id=item.scenario_id,
            version_number=item.version_number,
            changed_by_user_id=item.changed_by_user_id,
            snapshot=item.snapshot,
            created_at=item.created_at.isoformat(),
        )
        for item in versions
    ]


@router.get("/admin/users", response_model=list[UserRead])
def list_users(
    _: User = Depends(require_roles(UserRole.admin.value)), db: Session = Depends(get_db)
) -> list[User]:
    return db.query(User).order_by(User.id).all()


@router.get("/students", response_model=list[UserRead])
def list_students(
    _: User = Depends(require_roles(UserRole.teacher.value, UserRole.admin.value)),
    db: Session = Depends(get_db),
) -> list[User]:
    return (
        db.query(User)
        .filter(User.role == UserRole.student.value, User.is_active.is_(True))
        .order_by(User.display_name, User.id)
        .all()
    )


@router.get("/training-sessions", response_model=list[TrainingHistoryItem])
def list_training_history(
    user_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TrainingHistoryItem]:
    target = resolve_analytics_user(db, user, user_id)
    return TrainingAnalyticsService(db).history(target.id)


@router.get("/training-sessions/{session_id}/report", response_model=StoredTrainingReport)
def get_training_report(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StoredTrainingReport:
    session = authorize_session_view(db, session_id, user)
    try:
        return TrainingAnalyticsService(db).report(session)
    except ReportNotFound as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/ability-analysis", response_model=AbilityAnalysis)
def get_ability_analysis(
    user_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AbilityAnalysis:
    target = resolve_analytics_user(db, user, user_id)
    return TrainingAnalyticsService(db).abilities(target.id)


@router.post("/training-plans/generate", response_model=TrainingPlanRead)
async def generate_training_plan(
    user: User = Depends(require_roles(UserRole.student.value)),
    db: Session = Depends(get_db),
) -> TrainingPlanRead:
    return await TrainingPlanService(db).generate(user)


@router.get("/training-plans/current", response_model=TrainingPlanRead)
def get_current_training_plan(
    user_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrainingPlanRead:
    target = resolve_analytics_user(db, user, user_id)
    plan = TrainingPlanService(db).current(target.id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Training plan not found")
    return plan


@router.get("/training-plans", response_model=list[TrainingPlanRead])
def list_training_plans(
    user_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TrainingPlanRead]:
    target = resolve_analytics_user(db, user, user_id)
    return TrainingPlanService(db).history(target.id)


@router.post("/training-sessions", response_model=TrainingSessionRead)
def create_training_session(
    payload: TrainingSessionCreate,
    user: User = Depends(require_roles(UserRole.student.value)),
    db: Session = Depends(get_db),
) -> TrainingSession:
    try:
        return TrainingService(db).create_session(payload, user)
    except TrainingResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/training-sessions/{session_id}/actions", response_model=RuleCheckResult)
def submit_action(
    session_id: int, payload: TrainingActionCreate,
    user: User = Depends(require_roles(UserRole.student.value)), db: Session = Depends(get_db),
) -> RuleCheckResult:
    authorize_session_owner(db, session_id, user)
    try:
        rule_check = TrainingService(db).submit_action(session_id, payload)
    except TrainingResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTrainingState as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return RuleCheckResult(
        passed=rule_check.passed,
        score=rule_check.score,
        missing_steps=rule_check.missing_steps,
        violations=rule_check.violations,
        suggestions=rule_check.suggestions,
    )


@router.get(
    "/training-sessions/{session_id}/conversations",
    response_model=list[ConversationMessageRead],
)
def list_conversations(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConversationMessageRead]:
    authorize_session_view(db, session_id, user)
    return ConversationService(db).history(session_id)


@router.post(
    "/training-sessions/{session_id}/customer-messages",
    response_model=CustomerMessageResponse,
)
async def send_customer_message(
    session_id: int,
    payload: CustomerMessageCreate,
    user: User = Depends(require_roles(UserRole.student.value)),
    db: Session = Depends(get_db),
) -> CustomerMessageResponse:
    session = authorize_session_owner(db, session_id, user)
    if session.status != "active":
        raise HTTPException(status_code=409, detail="Customer conversation is available only in active sessions")
    return await ConversationService(db).talk(session, payload.message)


@router.post("/training-sessions/{session_id}/complete", response_model=FinalTrainingReport)
async def complete_training_session(
    session_id: int, user: User = Depends(require_roles(UserRole.student.value)),
    db: Session = Depends(get_db),
) -> FinalTrainingReport:
    authorize_session_owner(db, session_id, user)
    try:
        session, rule_check, score = TrainingService(db).complete_session(session_id)
    except TrainingResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTrainingState as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    examiner_context = {
        "scenario": session.scenario.title,
        "business_type": session.scenario.business_type,
        "performed_steps": session.context.get("performed_steps", []),
        "passed": rule_check.passed,
        "rule_score": rule_check.score,
        "missing_steps": rule_check.missing_steps,
        "violations": rule_check.violations,
        "recent_conversation": ConversationService.recent_context(session),
        "rule_engine_is_final_authority": True,
    }
    ai_generated = True
    try:
        examiner_result = await AgentOrchestrator().run(
            "examiner",
            "请解释本次训练表现、确定性扣分原因和下一步改进重点。不得改变规则引擎结论或分数。",
            examiner_context,
        )
        examiner_report = examiner_result.content
    except Exception:  # The external AI provider must not block deterministic final submission.
        ai_generated = False
        examiner_report = (
            f"规则引擎已完成最终判定：规则分 {rule_check.score}，"
            f"缺失步骤 {len(rule_check.missing_steps)} 项，风险违规 {len(rule_check.violations)} 项。"
            "AI 考官暂时不可用，请依据规则明细完成复盘。"
        )
    db.add(
        AIEvaluation(
            session_id=session_id,
            agent_name="examiner",
            result={"content": examiner_report, "rule_score": rule_check.score, "ai_generated": ai_generated},
        )
    )
    db.commit()

    return FinalTrainingReport(
        session_id=session.id,
        status=session.status,
        completed_at=session.completed_at.isoformat(),
        passed=rule_check.passed,
        rule_score=score.rule_score,
        total_score=score.total_score,
        missing_steps=rule_check.missing_steps,
        violations=rule_check.violations,
        suggestions=rule_check.suggestions,
        examiner_report=examiner_report,
    )


@router.post("/ai/evaluate", response_model=AIEvaluationResponse)
async def evaluate_with_agent(
    payload: AIEvaluationRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> AIEvaluationResponse:
    session = db.get(TrainingSession, payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Training session not found")
    if user.role == UserRole.student.value and session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Cannot access another student's training session")
    allowed_agents = {
        UserRole.student.value: {"coach"},
        UserRole.teacher.value: {"coach", "examiner", "scenario"},
        UserRole.admin.value: {"coach", "examiner", "scenario"},
    }
    if payload.agent_name not in allowed_agents.get(user.role, set()):
        raise HTTPException(status_code=403, detail="Agent is not available through this endpoint for the current role")

    agent_context = {
        **session.context,
        "scenario": {
            "title": session.scenario.title,
            "business_type": session.scenario.business_type,
        },
        "recent_conversation": ConversationService.recent_context(session),
        "rule_engine_is_final_authority": True,
    }

    try:
        result = await AgentOrchestrator().run(payload.agent_name, payload.learner_message, agent_context)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.add(AIEvaluation(session_id=payload.session_id, agent_name=result.agent_name, result={"content": result.content}))
    db.commit()
    return AIEvaluationResponse(agent_name=result.agent_name, content=result.content, metadata=result.metadata)


def authorize_session_owner(db: Session, session_id: int, user: User) -> TrainingSession:
    session = db.get(TrainingSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Training session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Cannot modify another student's training session")
    return session


def authorize_session_view(db: Session, session_id: int, user: User) -> TrainingSession:
    session = db.get(TrainingSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Training session not found")
    if user.role == UserRole.student.value and session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Cannot access another student's training session")
    return session


def resolve_analytics_user(db: Session, current_user: User, requested_user_id: int | None) -> User:
    if current_user.role == UserRole.student.value:
        if requested_user_id is not None and requested_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Cannot access another student's analytics")
        return current_user
    if requested_user_id is None:
        raise HTTPException(status_code=422, detail="user_id is required for teacher/admin analytics")
    target = db.get(User, requested_user_id)
    if target is None or target.role != UserRole.student.value:
        raise HTTPException(status_code=404, detail="Student not found")
    return target


def scenario_snapshot(scenario: Scenario) -> dict:
    return {
        "title": scenario.title,
        "business_type": scenario.business_type,
        "difficulty": scenario.difficulty,
        "description": scenario.description,
        "expected_steps": scenario.expected_steps,
        "risk_rules": scenario.risk_rules,
        "scoring_policy": scenario.scoring_policy,
        "rule_policy": scenario.rule_policy,
        "customer_profile": scenario.customer_profile,
    }
