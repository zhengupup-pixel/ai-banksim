from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.entities import Scenario, User, UserRole
from app.services.auth import hash_password
from app.services.demo_scenarios import DEMO_SCENARIOS


DEMO_USERS = [
    (1, "demo_student", "Demo Student", UserRole.student.value, "Student123!"),
    (2, "demo_teacher", "Demo Teacher", UserRole.teacher.value, "Teacher123!"),
    (3, "demo_admin", "Demo Admin", UserRole.admin.value, "Admin123!"),
]


def seed_demo_data(db: Session) -> None:
    for user_id, username, display_name, role, password in DEMO_USERS:
        user = db.get(User, user_id)
        if user is None:
            db.add(User(
                id=user_id, username=username, display_name=display_name,
                role=role, password_hash=hash_password(password), is_active=True,
            ))
        else:
            user.username = username
            user.display_name = display_name
            user.role = role
            user.password_hash = hash_password(password)
            user.is_active = True

    for scenario_data in DEMO_SCENARIOS:
        scenario = db.get(Scenario, scenario_data["id"])
        if scenario is None:
            db.add(Scenario(**scenario_data))
        else:
            for field, value in scenario_data.items():
                if field != "id":
                    setattr(scenario, field, value)
    db.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        seed_demo_data(session)
    print("Demo users and six training scenarios seeded.")
