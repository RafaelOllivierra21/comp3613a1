import json
import os
from datetime import date
from getpass import getpass
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app.models.application import (
    Application,
    InternshipCycle,
    Skill,
    Student,
    StudentSkill,
)
from app.models.position import Company, CompanyRep, Position, PositionSkill
from app.models.user import User
from app.utilities.security import encrypt_password, verify_password

PASSWORD_ENVIRONMENT_VARIABLE = "INTERNBRIDGE_SAMPLE_PASSWORD"
DEFAULT_FIXTURE_PATH = Path("docs/sample-data.json")


def _sample_password() -> str:
    password = os.environ.get(PASSWORD_ENVIRONMENT_VARIABLE)
    if password is None:
        password = getpass("Shared password for sample accounts: ")
    if not password:
        raise ValueError(
            f"{PASSWORD_ENVIRONMENT_VARIABLE} must contain a non-empty password."
        )
    return password


def _date(value: str) -> date:
    return date.fromisoformat(value)


def _get_or_create_user(
    session: Session,
    record: dict[str, Any],
    password: str,
    password_hash: str,
) -> User:
    username_user = session.exec(
        select(User).where(User.username == record["username"])
    ).one_or_none()
    email_user = session.exec(
        select(User).where(User.email == record["email"])
    ).one_or_none()
    if username_user is not None or email_user is not None:
        if username_user is None or email_user is None or username_user.id != email_user.id:
            raise ValueError(
                f"Sample account {record['username']} conflicts with an existing account."
            )
        if (
            username_user.fullName != record["fullName"]
            or username_user.number != record["number"]
            or username_user.role != record["role"]
            or not verify_password(password, username_user.password)
        ):
            raise ValueError(
                f"Existing account {record['username']} does not match the sample fixture."
            )
        return username_user

    user = User(
        username=record["username"],
        email=record["email"],
        fullName=record["fullName"],
        number=record["number"],
        password=password_hash,
        role=record["role"],
    )
    session.add(user)
    session.flush()
    return user


def _get_or_create_company(
    session: Session,
    record: dict[str, Any],
) -> Company:
    company = session.exec(
        select(Company).where(Company.name == record["name"])
    ).one_or_none()
    if company is not None:
        if company.location != record["location"]:
            raise ValueError(
                f"Existing company {record['name']} does not match the sample fixture."
            )
        return company

    company = Company(name=record["name"], location=record["location"])
    session.add(company)
    session.flush()
    return company


def _get_or_create_position(
    session: Session,
    record: dict[str, Any],
    company_id: int,
    cycle_id: int,
) -> Position:
    position = session.exec(
        select(Position).where(
            Position.companyID == company_id,
            Position.title == record["title"],
        )
    ).one_or_none()
    if position is not None:
        if (
            position.cycleID != cycle_id
            or position.description != record["description"]
            or position.dateOpened != _date(record["dateOpened"])
        ):
            raise ValueError(
                f"Existing position {record['title']} does not match the sample fixture."
            )
        return position

    position = Position(
        companyID=company_id,
        cycleID=cycle_id,
        title=record["title"],
        description=record["description"],
        dateOpened=_date(record["dateOpened"]),
        status=record["status"],
    )
    session.add(position)
    session.flush()
    return position


def _get_or_create_student_application(
    session: Session,
    record: dict[str, Any],
    user: User,
    cycle_id: int,
) -> Student:
    student = session.get(Student, record["studentID"])
    if student is not None:
        if (
            student.userID != user.id
            or student.gpa != record["gpa"]
            or student.degreeName != record["degreeName"]
            or student.expectedGraduationDate
            != _date(record["expectedGraduationDate"])
            or student.resumeLink != record["resumeLink"]
        ):
            raise ValueError(
                f"Existing student {record['studentID']} does not match the sample fixture."
            )
    else:
        student = Student(
            studentID=record["studentID"],
            userID=user.id,
            gpa=record["gpa"],
            degreeName=record["degreeName"],
            expectedGraduationDate=_date(record["expectedGraduationDate"]),
            resumeLink=record["resumeLink"],
        )
        session.add(student)
        session.flush()

    application = session.exec(
        select(Application).where(
            Application.studentID == student.studentID,
            Application.cycleID == cycle_id,
        )
    ).one_or_none()
    if application is None:
        session.add(
            Application(
                studentID=student.studentID,
                cycleID=cycle_id,
                dateSubmitted=_date(record["dateSubmitted"]),
                status=record["applicationStatus"],
            )
        )
        session.flush()
    elif application.dateSubmitted != _date(record["dateSubmitted"]):
        raise ValueError(
            f"Existing application for student {record['studentID']} "
            "does not match the sample fixture."
        )

    return student


def seed_sample_data(
    fixture_path: Path = DEFAULT_FIXTURE_PATH,
) -> dict[str, int]:
    from app.database import ensure_db_and_tables, get_cli_session
    import app.models  # noqa: F401

    ensure_db_and_tables()
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    password = _sample_password()
    hashed_password = encrypt_password(password)
    company_ids: dict[str, int] = {}
    counts = {"users": 0, "companies": 0, "positions": 0, "students": 0}
    from app.database import engine

    echo_setting = engine.echo
    engine.echo = False
    try:
        with get_cli_session() as session:
            try:
                cycles = session.exec(select(InternshipCycle)).all()
                if len(cycles) != 1:
                    raise ValueError(
                        "Sample data requires exactly one existing internship cycle."
                    )
                cycle = cycles[0]
                if (
                    cycle.startDate != _date(fixture["cycle"]["startDate"])
                    or cycle.endDate != _date(fixture["cycle"]["endDate"])
                    or cycle.status.casefold() != fixture["cycle"]["status"].casefold()
                ):
                    raise ValueError(
                        "The existing internship cycle does not match the sample fixture."
                    )
                if cycle.cycleID is None:
                    raise ValueError("The internship cycle must have a database ID.")

                users_by_key: dict[str, User] = {}
                for record in fixture["users"]:
                    existing = session.exec(
                        select(User).where(
                            (User.username == record["username"])
                            | (User.email == record["email"])
                        )
                    ).first()
                    user = _get_or_create_user(
                        session,
                        record,
                        password,
                        hashed_password,
                    )
                    if existing is None:
                        counts["users"] += 1
                    users_by_key[record["key"]] = user
                    if user.id is None:
                        raise ValueError(
                            f"Sample account {record['username']} has no ID."
                        )

                for record in fixture["companies"]:
                    existing = session.exec(
                        select(Company).where(Company.name == record["name"])
                    ).one_or_none()
                    company = _get_or_create_company(session, record)
                    if existing is None:
                        counts["companies"] += 1
                    if company.companyID is None:
                        raise ValueError(
                            f"Company {record['name']} has no database ID."
                        )
                    company_ids[record["key"]] = company.companyID

                    user = users_by_key[record["representativeUserKey"]]
                    representative = session.exec(
                        select(CompanyRep).where(
                            (CompanyRep.userID == user.id)
                            | (CompanyRep.companyID == company.companyID)
                        )
                    ).first()
                    if representative is None:
                        session.add(
                            CompanyRep(
                                userID=user.id,
                                companyID=company.companyID,
                            )
                        )
                        session.flush()
                    elif (
                        representative.userID != user.id
                        or representative.companyID != company.companyID
                    ):
                        raise ValueError(
                            f"Existing representative relationship for {record['name']} "
                            "does not match the sample fixture."
                        )

                skills = {
                    skill.name: skill
                    for skill in session.exec(select(Skill)).all()
                }
                all_skill_names = {
                    skill_name
                    for record in fixture["positions"]
                    for skill_name in record["requiredSkills"]
                } | {
                    skill_name
                    for record in fixture["students"]
                    for skill_name in record["skills"]
                }
                for skill_name in sorted(all_skill_names - skills.keys()):
                    skill = Skill(name=skill_name)
                    session.add(skill)
                    session.flush()
                    skills[skill_name] = skill

                for record in fixture["positions"]:
                    existing_position = session.exec(
                        select(Position).where(
                            Position.companyID == company_ids[record["companyKey"]],
                            Position.title == record["title"],
                        )
                    ).one_or_none()
                    position = _get_or_create_position(
                        session,
                        record,
                        company_ids[record["companyKey"]],
                        cycle.cycleID,
                    )
                    if existing_position is None:
                        counts["positions"] += 1
                    if position.positionID is None:
                        raise ValueError(
                            f"Position {record['title']} has no database ID."
                        )
                    for skill_name in record["requiredSkills"]:
                        skill = skills[skill_name]
                        existing_link = session.get(
                            PositionSkill,
                            (position.positionID, skill.skillID),
                        )
                        if existing_link is None:
                            session.add(
                                PositionSkill(
                                    positionID=position.positionID,
                                    skillID=skill.skillID,
                                )
                            )

                for record in fixture["students"]:
                    user = users_by_key[record["key"]]
                    existing_student = session.get(Student, record["studentID"])
                    student = _get_or_create_student_application(
                        session,
                        record,
                        user,
                        cycle.cycleID,
                    )
                    if existing_student is None:
                        counts["students"] += 1
                    for skill_name in record["skills"]:
                        skill = skills[skill_name]
                        existing_link = session.get(
                            StudentSkill,
                            (student.studentID, skill.skillID),
                        )
                        if existing_link is None:
                            session.add(
                                StudentSkill(
                                    studentID=student.studentID,
                                    skillID=skill.skillID,
                                )
                            )

                session.commit()
            except Exception:
                session.rollback()
                raise
    finally:
        engine.echo = echo_setting

    return counts
