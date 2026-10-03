import logging

from sqlmodel import Session, func, select

from app.models.application import (
    Application,
    InternshipCycle,
    Skill,
    Student,
    StudentSkill,
)
from app.models.position import Company, Match, Position, PositionSkill
from app.models.user import User

logger = logging.getLogger(__name__)


class MatchingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_current_cycle(self) -> InternshipCycle | None:
        return self.db.exec(select(InternshipCycle)).one_or_none()

    def get_cycle(self, cycle_id: int) -> InternshipCycle | None:
        return self.db.get(InternshipCycle, cycle_id)

    def get_application(self, application_id: int) -> Application | None:
        return self.db.get(Application, application_id)

    def get_position(self, position_id: int) -> Position | None:
        return self.db.get(Position, position_id)

    def get_student(self, student_id: int) -> Student | None:
        return self.db.get(Student, student_id)

    def get_user(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def has_match(self, application_id: int, position_id: int) -> bool:
        statement = select(Match.matchID).where(
            Match.applicationID == application_id,
            Match.positionID == position_id,
        )
        return self.db.exec(statement).first() is not None

    def create_match(self, application: Application, match: Match) -> Match:
        try:
            self.db.add(application)
            self.db.add(match)
            self.db.commit()
            self.db.refresh(match)
            return match
        except Exception as exc:
            logger.error("Unable to save internship match: %s", exc)
            self.db.rollback()
            raise

    def get_student_skill_ids(self, student_id: int) -> set[int]:
        statement = select(StudentSkill.skillID).where(
            StudentSkill.studentID == student_id
        )
        return set(self.db.exec(statement).all())

    def get_student_skills(self, student_id: int) -> list[Skill]:
        statement = (
            select(Skill)
            .join(StudentSkill, StudentSkill.skillID == Skill.skillID)
            .where(StudentSkill.studentID == student_id)
            .order_by(Skill.name)
        )
        return self.db.exec(statement).all()

    def get_open_positions_for_cycle(
        self,
        cycle_id: int,
    ) -> list[tuple[Position, Company]]:
        statement = (
            select(Position, Company)
            .join(Company, Position.companyID == Company.companyID)
            .where(
                Position.cycleID == cycle_id,
                func.lower(Position.status) == "open",
            )
        )
        return self.db.exec(statement).all()

    def get_required_skill_ids(
        self,
        position_ids: list[int],
    ) -> dict[int, set[int]]:
        if not position_ids:
            return {}
        statement = select(
            PositionSkill.positionID,
            PositionSkill.skillID,
        ).where(PositionSkill.positionID.in_(position_ids))
        required_skills: dict[int, set[int]] = {}
        for position_id, skill_id in self.db.exec(statement).all():
            required_skills.setdefault(position_id, set()).add(skill_id)
        return required_skills

    def get_current_matches(
        self,
        application_id: int,
    ) -> list[tuple[Match, Position, Company]]:
        statement = (
            select(Match, Position, Company)
            .join(Position, Match.positionID == Position.positionID)
            .join(Company, Position.companyID == Company.companyID)
            .where(Match.applicationID == application_id)
            .order_by(Position.title, Company.name, Position.positionID)
        )
        return self.db.exec(statement).all()

    def get_applications_for_cycle(
        self,
        cycle_id: int,
    ) -> list[tuple[Application, Student, User]]:
        statement = (
            select(Application, Student, User)
            .join(Student, Application.studentID == Student.studentID)
            .join(User, Student.userID == User.id)
            .where(Application.cycleID == cycle_id)
            .order_by(User.fullName, Application.applicationID)
        )
        return self.db.exec(statement).all()

    def get_active_match_counts(self, cycle_id: int) -> dict[int, int]:
        statement = (
            select(Application.applicationID, func.count(Match.matchID))
            .join(Match, Match.applicationID == Application.applicationID)
            .where(
                Application.cycleID == cycle_id,
                func.lower(Match.status).in_(("matched", "interviewing", "offered")),
            )
            .group_by(Application.applicationID)
        )
        return {
            application_id: count
            for application_id, count in self.db.exec(statement).all()
        }
