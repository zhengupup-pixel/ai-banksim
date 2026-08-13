from fastapi.testclient import TestClient

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.main import app
from app.models.entities import AuthToken, User, UserRole
from app.services.auth import hash_password, hash_token


init_db()
client = TestClient(app)


def login_headers(username: str = "demo_student", password: str = "Student123!") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_seed_and_training_flow() -> None:
    seed = client.post("/api/dev/seed")
    assert seed.status_code == 200
    headers = login_headers()

    scenarios = client.get("/api/scenarios", headers=headers)
    assert scenarios.status_code == 200
    assert scenarios.json()[0]["title"] == "个人活期账户开户"
    assert len(scenarios.json()) == 6
    assert scenarios.json()[1]["business_type"] == "deposit"

    session = client.post("/api/training-sessions", json={"scenario_id": 1}, headers=headers)
    assert session.status_code == 200
    session_id = session.json()["id"]

    action = client.post(
        f"/api/training-sessions/{session_id}/actions",
        json={"action_type": "greet_customer", "payload": {}},
        headers=headers,
    )
    assert action.status_code == 200
    assert action.json()["passed"] is False
    assert "verify_identity" in action.json()["missing_steps"]


def test_mock_ai_coach() -> None:
    client.post("/api/dev/seed")
    headers = login_headers()
    session = client.post("/api/training-sessions", json={"scenario_id": 1}, headers=headers)
    response = client.post(
        "/api/ai/evaluate",
        json={"session_id": session.json()["id"], "agent_name": "coach", "learner_message": "下一步该做什么？"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["agent_name"] == "coach"
    assert "Mock AI" in response.json()["content"]


def test_complete_training_creates_final_rule_report_and_locks_session() -> None:
    client.post("/api/dev/seed")
    headers = login_headers()
    scenario = client.get("/api/scenarios", headers=headers).json()[0]
    created = client.post("/api/training-sessions", json={"scenario_id": scenario["id"]}, headers=headers)
    session_id = created.json()["id"]

    business_data = {"presented_id_number": "ID001", "customer_id_number": "ID001"}
    for index, step in enumerate(scenario["expected_steps"]):
        response = client.post(
            f"/api/training-sessions/{session_id}/actions",
            json={"action_type": step, "payload": business_data if index == 0 else {}},
            headers=headers,
        )
        assert response.status_code == 200

    completed = client.post(f"/api/training-sessions/{session_id}/complete", headers=headers)
    assert completed.status_code == 200
    report = completed.json()
    assert report["status"] == "completed"
    assert report["passed"] is True
    assert report["rule_score"] == 100
    assert report["total_score"] == 100
    assert report["missing_steps"] == []
    assert "Mock AI" in report["examiner_report"]

    late_action = client.post(
        f"/api/training-sessions/{session_id}/actions",
        json={"action_type": "confirm_receipt", "payload": {}},
        headers=headers,
    )
    assert late_action.status_code == 409

    duplicate_completion = client.post(f"/api/training-sessions/{session_id}/complete", headers=headers)
    assert duplicate_completion.status_code == 409


def test_complete_incomplete_training_preserves_rule_engine_failure() -> None:
    client.post("/api/dev/seed")
    headers = login_headers()
    created = client.post("/api/training-sessions", json={"scenario_id": 1}, headers=headers)

    completed = client.post(f"/api/training-sessions/{created.json()['id']}/complete", headers=headers)

    assert completed.status_code == 200
    report = completed.json()
    assert report["passed"] is False
    assert report["rule_score"] == 0
    assert report["total_score"] == 0
    assert "verify_identity" in report["missing_steps"]


def test_training_session_requires_authentication() -> None:
    client.post("/api/dev/seed")
    response = client.post("/api/training-sessions", json={"scenario_id": 1})
    assert response.status_code == 401


def test_complete_training_falls_back_when_examiner_provider_fails(monkeypatch) -> None:
    async def fail_provider(*_args, **_kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("app.api.routes.AgentOrchestrator.run", fail_provider)
    client.post("/api/dev/seed")
    headers = login_headers()
    created = client.post("/api/training-sessions", json={"scenario_id": 1}, headers=headers)

    completed = client.post(f"/api/training-sessions/{created.json()['id']}/complete", headers=headers)

    assert completed.status_code == 200
    report = completed.json()
    assert report["status"] == "completed"
    assert report["passed"] is False
    assert "规则引擎已完成最终判定" in report["examiner_report"]
    assert "AI 考官暂时不可用" in report["examiner_report"]


def test_large_deposit_requires_review_before_posting() -> None:
    client.post("/api/dev/seed")
    headers = login_headers()
    scenarios = client.get("/api/scenarios", headers=headers).json()
    deposit = next(item for item in scenarios if item["business_type"] == "deposit")
    created = client.post("/api/training-sessions", json={"scenario_id": deposit["id"]}, headers=headers)
    session_id = created.json()["id"]
    data = {"amount": 60000, "account_number": "A001", "customer_account_number": "A001"}

    for step in deposit["expected_steps"]:
        client.post(
            f"/api/training-sessions/{session_id}/actions",
            json={"action_type": step, "payload": data},
            headers=headers,
        )
    late_review = client.post(
        f"/api/training-sessions/{session_id}/actions",
        json={"action_type": "large_cash_review", "payload": data},
        headers=headers,
    )

    assert late_review.status_code == 200
    assert late_review.json()["passed"] is False
    assert "大额现金复核必须在存款入账前完成。" in late_review.json()["violations"]


def test_login_me_logout_and_revocation() -> None:
    client.post("/api/dev/seed")
    headers = login_headers()
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "student"

    logout = client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_student_cannot_update_scenario_but_teacher_can() -> None:
    client.post("/api/dev/seed")
    student_headers = login_headers()
    teacher_headers = login_headers("demo_teacher", "Teacher123!")
    scenario = client.get("/api/scenarios", headers=student_headers).json()[0]
    scenario["title"] = "教师更新的开户场景"

    denied = client.put(f"/api/scenarios/{scenario['id']}", json=scenario, headers=student_headers)
    assert denied.status_code == 403
    updated = client.put(f"/api/scenarios/{scenario['id']}", json=scenario, headers=teacher_headers)
    assert updated.status_code == 200
    assert updated.json()["title"] == "教师更新的开户场景"
    versions = client.get(f"/api/scenarios/{scenario['id']}/versions", headers=teacher_headers)
    assert versions.status_code == 200
    assert versions.json()[0]["version_number"] >= 1
    assert versions.json()[0]["snapshot"]["title"] != updated.json()["title"]
    assert client.get(f"/api/scenarios/{scenario['id']}/versions", headers=student_headers).status_code == 403


def test_only_admin_can_list_users() -> None:
    client.post("/api/dev/seed")
    teacher_headers = login_headers("demo_teacher", "Teacher123!")
    admin_headers = login_headers("demo_admin", "Admin123!")
    assert client.get("/api/admin/users", headers=teacher_headers).status_code == 403
    users = client.get("/api/admin/users", headers=admin_headers)
    assert users.status_code == 200
    assert {user["role"] for user in users.json()} == {"student", "teacher", "admin"}
    students = client.get("/api/students", headers=teacher_headers)
    assert students.status_code == 200
    assert all(user["role"] == "student" for user in students.json())


def test_invalid_password_is_rejected_and_raw_token_is_not_stored() -> None:
    client.post("/api/dev/seed")
    rejected = client.post(
        "/api/auth/login", json={"username": "demo_student", "password": "WrongPass123!"}
    )
    assert rejected.status_code == 401

    login = client.post(
        "/api/auth/login", json={"username": "demo_student", "password": "Student123!"}
    )
    raw_token = login.json()["access_token"]
    with SessionLocal() as db:
        stored = db.query(AuthToken).filter(AuthToken.token_hash == hash_token(raw_token)).one()
        assert stored.token_hash != raw_token


def test_teacher_cannot_start_student_training() -> None:
    client.post("/api/dev/seed")
    teacher_headers = login_headers("demo_teacher", "Teacher123!")
    response = client.post("/api/training-sessions", json={"scenario_id": 1}, headers=teacher_headers)
    assert response.status_code == 403


def test_student_cannot_modify_another_students_session() -> None:
    client.post("/api/dev/seed")
    first_headers = login_headers()
    created = client.post("/api/training-sessions", json={"scenario_id": 1}, headers=first_headers)

    with SessionLocal() as db:
        second = User(
            username="second_student", display_name="Second Student", role=UserRole.student.value,
            password_hash=hash_password("SecondStudent123!"), is_active=True,
        )
        db.add(second)
        db.commit()
    second_headers = login_headers("second_student", "SecondStudent123!")

    response = client.post(
        f"/api/training-sessions/{created.json()['id']}/actions",
        json={"action_type": "greet_customer", "payload": {}},
        headers=second_headers,
    )
    assert response.status_code == 403


def test_training_history_report_and_ability_analysis() -> None:
    client.post("/api/dev/seed")
    with SessionLocal() as db:
        learner = User(
            username="analytics_student", display_name="Analytics Student", role=UserRole.student.value,
            password_hash=hash_password("AnalyticsStudent123!"), is_active=True,
        )
        db.add(learner)
        db.commit()
    headers = login_headers("analytics_student", "AnalyticsStudent123!")
    scenarios = client.get("/api/scenarios", headers=headers).json()

    opening = next(item for item in scenarios if item["business_type"] == "account_opening")
    passed_session = client.post(
        "/api/training-sessions", json={"scenario_id": opening["id"]}, headers=headers
    ).json()
    identity = {"presented_id_number": "ID001", "customer_id_number": "ID001"}
    for step in opening["expected_steps"]:
        client.post(
            f"/api/training-sessions/{passed_session['id']}/actions",
            json={"action_type": step, "payload": identity}, headers=headers,
        )
    assert client.post(
        f"/api/training-sessions/{passed_session['id']}/complete", headers=headers
    ).status_code == 200

    withdrawal = next(item for item in scenarios if item["business_type"] == "withdrawal")
    failed_session = client.post(
        "/api/training-sessions", json={"scenario_id": withdrawal["id"]}, headers=headers
    ).json()
    assert client.post(
        f"/api/training-sessions/{failed_session['id']}/complete", headers=headers
    ).status_code == 200

    history = client.get("/api/training-sessions", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 2
    assert {item["passed"] for item in history.json()} == {True, False}

    report = client.get(
        f"/api/training-sessions/{passed_session['id']}/report", headers=headers
    )
    assert report.status_code == 200
    assert report.json()["scenario_title"] == opening["title"]
    assert report.json()["rule_score"] == 100
    assert "Mock AI" in report.json()["examiner_report"]

    analysis = client.get("/api/ability-analysis", headers=headers)
    assert analysis.status_code == 200
    assert analysis.json()["completed_sessions"] == 2
    assert analysis.json()["average_score"] == 50
    assert analysis.json()["pass_rate"] == 50
    assert "withdrawal" in analysis.json()["recommended_business_types"]
    assert any("缺失步骤" in weakness["category"] for weakness in analysis.json()["weaknesses"])


def test_analytics_role_and_ownership_boundaries() -> None:
    client.post("/api/dev/seed")
    student_headers = login_headers()
    teacher_headers = login_headers("demo_teacher", "Teacher123!")
    created = client.post("/api/training-sessions", json={"scenario_id": 1}, headers=student_headers).json()

    assert client.get("/api/training-sessions?user_id=999999", headers=student_headers).status_code == 403
    assert client.get("/api/ability-analysis", headers=teacher_headers).status_code == 422
    teacher_history = client.get("/api/training-sessions?user_id=1", headers=teacher_headers)
    assert teacher_history.status_code == 200
    assert any(item["session_id"] == created["id"] for item in teacher_history.json())
    active_report = client.get(
        f"/api/training-sessions/{created['id']}/report", headers=teacher_headers
    )
    assert active_report.status_code == 409


def test_customer_conversation_is_scenario_specific_and_persisted() -> None:
    client.post("/api/dev/seed")
    headers = login_headers()
    scenarios = client.get("/api/scenarios", headers=headers).json()
    loss_report = next(item for item in scenarios if item["business_type"] == "loss_reporting")
    assert loss_report["customer_profile"]["name"] == "孙悦"
    assert "internal_notes" not in loss_report["customer_profile"]
    created = client.post(
        "/api/training-sessions", json={"scenario_id": loss_report["id"]}, headers=headers
    ).json()

    response = client.post(
        f"/api/training-sessions/{created['id']}/customer-messages",
        json={"message": "您好，请问您需要办理什么业务？"}, headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["learner_message"]["speaker"] == "learner"
    assert response.json()["customer_message"]["speaker"] == "customer"
    assert "模拟客户" in response.json()["customer_message"]["message"]
    history = client.get(
        f"/api/training-sessions/{created['id']}/conversations", headers=headers
    )
    assert [item["speaker"] for item in history.json()] == ["learner", "customer"]


def test_customer_conversation_falls_back_and_locks_after_completion(monkeypatch) -> None:
    async def fail_provider(*_args, **_kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("app.services.conversation.AgentOrchestrator.run", fail_provider)
    client.post("/api/dev/seed")
    headers = login_headers()
    scenario = client.get("/api/scenarios", headers=headers).json()[0]
    created = client.post(
        "/api/training-sessions", json={"scenario_id": scenario["id"]}, headers=headers
    ).json()
    conversation = client.post(
        f"/api/training-sessions/{created['id']}/customer-messages",
        json={"message": "您好"}, headers=headers,
    )
    assert conversation.status_code == 200
    assert conversation.json()["ai_generated"] is False
    assert conversation.json()["customer_message"]["message"] == scenario["customer_profile"]["opening_line"]

    client.post(f"/api/training-sessions/{created['id']}/complete", headers=headers)
    locked = client.post(
        f"/api/training-sessions/{created['id']}/customer-messages",
        json={"message": "还有问题"}, headers=headers,
    )
    assert locked.status_code == 409


def test_student_cannot_read_another_students_conversation() -> None:
    client.post("/api/dev/seed")
    owner_headers = login_headers()
    created = client.post(
        "/api/training-sessions", json={"scenario_id": 1}, headers=owner_headers
    ).json()
    with SessionLocal() as db:
        other = User(
            username="conversation_other", display_name="Conversation Other",
            role=UserRole.student.value, password_hash=hash_password("ConversationOther123!"), is_active=True,
        )
        db.add(other)
        db.commit()
    other_headers = login_headers("conversation_other", "ConversationOther123!")
    response = client.get(
        f"/api/training-sessions/{created['id']}/conversations", headers=other_headers
    )
    assert response.status_code == 403


def test_generate_and_read_personalized_training_plan() -> None:
    client.post("/api/dev/seed")
    with SessionLocal() as db:
        learner = User(
            username="plan_student", display_name="Plan Student", role=UserRole.student.value,
            password_hash=hash_password("PlanStudent123!"), is_active=True,
        )
        db.add(learner)
        db.commit()
    headers = login_headers("plan_student", "PlanStudent123!")

    generated = client.post("/api/training-plans/generate", headers=headers)

    assert generated.status_code == 200
    plan = generated.json()
    assert len(plan["items"]) == 3
    assert [item["business_type"] for item in plan["items"]] == [
        "account_opening", "deposit", "loss_reporting"
    ]
    assert all(item["source"] == "untrained_business" for item in plan["items"])
    assert len(plan["recommendations"]) == 3
    assert "Mock AI" in plan["planner_explanation"]

    current = client.get("/api/training-plans/current", headers=headers)
    history = client.get("/api/training-plans", headers=headers)
    assert current.status_code == 200
    assert current.json()["id"] == plan["id"]
    assert history.status_code == 200
    assert history.json()[0]["id"] == plan["id"]


def test_plan_generation_fallback_and_review_permissions(monkeypatch) -> None:
    async def fail_provider(*_args, **_kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("app.services.planning.AgentOrchestrator.run", fail_provider)
    client.post("/api/dev/seed")
    student_headers = login_headers()
    teacher_headers = login_headers("demo_teacher", "Teacher123!")

    generated = client.post("/api/training-plans/generate", headers=student_headers)
    assert generated.status_code == 200
    assert generated.json()["ai_generated"] is False
    assert "确定性能力分析" in generated.json()["planner_explanation"]

    teacher_review = client.get("/api/training-plans/current?user_id=1", headers=teacher_headers)
    assert teacher_review.status_code == 200
    assert teacher_review.json()["user_id"] == 1
    assert client.post("/api/training-plans/generate", headers=teacher_headers).status_code == 403


def test_student_cannot_invoke_planner_through_generic_agent_endpoint() -> None:
    client.post("/api/dev/seed")
    headers = login_headers()
    created = client.post("/api/training-sessions", json={"scenario_id": 1}, headers=headers).json()
    response = client.post(
        "/api/ai/evaluate",
        json={"session_id": created["id"], "agent_name": "planner", "learner_message": "修改计划"},
        headers=headers,
    )
    assert response.status_code == 403
