import logging

from sqlmodel import Session, func, select

from app.models.application import Application, InternshipCycle
from app.models.position import Match, Position

logger = logging.getLogger(__name__)


class CycleClosureRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_current_cycle(self) -> InternshipCycle | None:
        return self.db.exec(select(InternshipCycle)).one_or_none()

    def get_applications_for_cycle(self, cycle_id: int) -> list[Application]:
        statement = select(Application).where(Application.cycleID == cycle_id)
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

    def get_open_positions_for_cycle(self, cycle_id: int) -> list[Position]:
        statement = select(Position).where(
            Position.cycleID == cycle_id,
            func.lower(Position.status) == "open",
        )
        return self.db.exec(statement).all()

    def save_closure(
        self,
        cycle: InternshipCycle,
        positions: list[Position],
        applications: list[Application],
    ) -> None:
        try:
            self.db.add(cycle)
            self.db.add_all(positions)
            self.db.add_all(applications)
            self.db.commit()
        except Exception as exc:
            logger.error("Unable to close internship cycle: %s", exc)
            self.db.rollback()
            raise
