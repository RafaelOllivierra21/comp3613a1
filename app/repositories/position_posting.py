import logging

from sqlmodel import Session, select

from app.models.application import InternshipCycle, Skill
from app.models.position import Company, CompanyRep, Position, PositionSkill

logger = logging.getLogger(__name__)


class PositionPostingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_company_rep_for_user(self, user_id: int) -> CompanyRep | None:
        statement = select(CompanyRep).where(CompanyRep.userID == user_id)
        return self.db.exec(statement).one_or_none()

    def get_company(self, company_id: int) -> Company | None:
        return self.db.get(Company, company_id)

    def get_current_cycle(self) -> InternshipCycle | None:
        return self.db.exec(select(InternshipCycle)).one_or_none()

    def get_all_skills(self) -> list[Skill]:
        return self.db.exec(select(Skill).order_by(Skill.name)).all()

    def get_skills_by_ids(self, skill_ids: list[int]) -> list[Skill]:
        if not skill_ids:
            return []
        statement = select(Skill).where(Skill.skillID.in_(skill_ids))
        return self.db.exec(statement).all()

    def create_position(
        self,
        position: Position,
        skill_ids: list[int],
    ) -> Position:
        try:
            self.db.add(position)
            self.db.flush()
            if position.positionID is None:
                raise RuntimeError("The database did not assign an internship position ID.")
            self.db.add_all(
                PositionSkill(positionID=position.positionID, skillID=skill_id)
                for skill_id in skill_ids
            )
            self.db.commit()
            self.db.refresh(position)
            return position
        except Exception as exc:
            logger.error("Unable to save internship position: %s", exc)
            self.db.rollback()
            raise
