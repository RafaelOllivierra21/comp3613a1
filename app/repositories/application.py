import logging
from typing import Optional

from sqlmodel import Session, select

from app.models.application import (
    Application,
    InternshipCycle,
    Skill,
    Student,
    StudentSkill,
)

logger = logging.getLogger(__name__)


class ApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_current_cycle(self) -> Optional[InternshipCycle]:
        return self.db.exec(select(InternshipCycle)).one_or_none()

    def get_student_by_id(self, student_id: int) -> Optional[Student]:
        return self.db.get(Student, student_id)

    def get_student_by_user_id(self, user_id: int) -> Optional[Student]:
        statement = select(Student).where(Student.userID == user_id)
        return self.db.exec(statement).one_or_none()

    def get_application_for_student_cycle(
        self,
        student_id: int,
        cycle_id: int,
    ) -> Optional[Application]:
        statement = select(Application).where(
            Application.studentID == student_id,
            Application.cycleID == cycle_id,
        )
        return self.db.exec(statement).one_or_none()

    def get_application_for_user_cycle(
        self,
        user_id: int,
        cycle_id: int,
    ) -> Optional[Application]:
        statement = (
            select(Application)
            .join(Student, Application.studentID == Student.studentID)
            .where(Student.userID == user_id, Application.cycleID == cycle_id)
        )
        return self.db.exec(statement).one_or_none()

    def get_all_skills(self) -> list[Skill]:
        return self.db.exec(select(Skill).order_by(Skill.name)).all()

    def get_skills_by_ids(self, skill_ids: list[int]) -> list[Skill]:
        if not skill_ids:
            return []
        statement = select(Skill).where(Skill.skillID.in_(skill_ids))
        return self.db.exec(statement).all()

    def get_skills_for_student(self, student_id: int) -> list[Skill]:
        statement = (
            select(Skill)
            .join(StudentSkill, StudentSkill.skillID == Skill.skillID)
            .where(StudentSkill.studentID == student_id)
            .order_by(Skill.name)
        )
        return self.db.exec(statement).all()

    def create_submission(
        self,
        student: Student,
        application: Application,
        skill_ids: list[int],
    ) -> Application:
        try:
            self.db.add(student)
            self.db.flush()
            self.db.add(application)
            self.db.add_all(
                StudentSkill(studentID=student.studentID, skillID=skill_id)
                for skill_id in skill_ids
            )
            self.db.commit()
            self.db.refresh(application)
            return application
        except Exception as exc:
            logger.error("Unable to save internship application: %s", exc)
            self.db.rollback()
            raise
