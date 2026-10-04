import logging

from sqlmodel import Session, select

from app.models.application import (
    Application,
    InternshipCycle,
    Student,
)
from app.models.position import (
    Company,
    CompanyRep,
    Match,
    Position,
)
from app.models.user import User

logger = logging.getLogger(__name__)
ACTIVE_MATCH_STATUSES = ("matched", "interviewing", "offered")


class CandidateSelectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_company_rep_for_user(self, user_id: int) -> CompanyRep | None:
        statement = select(CompanyRep).where(CompanyRep.userID == user_id)
        return self.db.exec(statement).one_or_none()

    def get_match(self, match_id: int) -> Match | None:
        return self.db.get(Match, match_id)

    def get_position(self, position_id: int) -> Position | None:
        return self.db.get(Position, position_id)

    def get_application(self, application_id: int) -> Application | None:
        return self.db.get(Application, application_id)

    def get_student_for_user(self, user_id: int) -> Student | None:
        statement = select(Student).where(Student.userID == user_id)
        return self.db.exec(statement).one_or_none()

    def get_current_cycle(self) -> InternshipCycle | None:
        return self.db.exec(select(InternshipCycle)).one_or_none()

    def get_cycle(self, cycle_id: int) -> InternshipCycle | None:
        return self.db.get(InternshipCycle, cycle_id)

    def get_application_for_student_cycle(
        self,
        student_id: int,
        cycle_id: int,
    ) -> Application | None:
        statement = select(Application).where(
            Application.studentID == student_id,
            Application.cycleID == cycle_id,
        )
        return self.db.exec(statement).one_or_none()

    def get_matches_for_application(self, application_id: int) -> list[Match]:
        statement = (
            select(Match)
            .where(Match.applicationID == application_id)
            .order_by(Match.matchDate, Match.matchID)
        )
        return self.db.exec(statement).all()

    def get_matches_for_position(self, position_id: int) -> list[Match]:
        statement = select(Match).where(Match.positionID == position_id)
        return self.db.exec(statement).all()

    def get_student_match_records(
        self,
        application_id: int,
    ) -> list[tuple[Match, Position, Company]]:
        statement = (
            select(Match, Position, Company)
            .join(Position, Match.positionID == Position.positionID)
            .join(Company, Position.companyID == Company.companyID)
            .where(Match.applicationID == application_id)
            .order_by(Match.matchDate, Match.matchID)
        )
        return self.db.exec(statement).all()

    def get_company_positions(self, company_id: int) -> list[Position]:
        statement = (
            select(Position)
            .where(Position.companyID == company_id)
            .order_by(Position.title, Position.positionID)
        )
        return self.db.exec(statement).all()

    def get_company_candidate_records(
        self,
        company_id: int,
    ) -> list[tuple[Match, Application, Student, User, Position]]:
        statement = (
            select(Match, Application, Student, User, Position)
            .join(Position, Match.positionID == Position.positionID)
            .join(Application, Match.applicationID == Application.applicationID)
            .join(Student, Application.studentID == Student.studentID)
            .join(User, Student.userID == User.id)
            .where(Position.companyID == company_id)
            .order_by(Position.title, User.fullName, Match.matchID)
        )
        return self.db.exec(statement).all()

    def has_pending_offer(
        self,
        position_id: int,
        exclude_match_id: int,
    ) -> bool:
        statement = select(Match.matchID).where(
            Match.positionID == position_id,
            Match.matchID != exclude_match_id,
            Match.status.ilike("offered"),
        )
        return self.db.exec(statement).first() is not None

    def has_active_matches(self, application_id: int) -> bool:
        statement = select(Match.matchID).where(
            Match.applicationID == application_id,
            Match.status.in_(ACTIVE_MATCH_STATUSES),
        )
        return self.db.exec(statement).first() is not None

    def save_changes(self) -> None:
        try:
            self.db.commit()
        except Exception as exc:
            logger.error("Unable to save candidate selection changes: %s", exc)
            self.db.rollback()
            raise
