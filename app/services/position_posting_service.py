from dataclasses import dataclass
from datetime import date

from app.models.application import InternshipCycle, Skill
from app.models.position import Company, CompanyRep, Position
from app.models.user import User
from app.repositories.position_posting import PositionPostingRepository
from app.services.application_service import CycleClosedError
from app.services.candidate_selection_service import NotACompanyRepError


class PositionPostingError(Exception):
    pass


class InvalidTitleInputError(PositionPostingError):
    pass


class InvalidDescriptionInputError(PositionPostingError):
    pass


class InvalidSkillInputError(PositionPostingError):
    pass


@dataclass(frozen=True)
class PositionPostingFormState:
    company: Company
    cycle: InternshipCycle
    available_skills: list[Skill]

    @property
    def cycle_is_open(self) -> bool:
        return self.cycle.status.strip().casefold() == "open"


class PositionPostingService:
    def __init__(self, repository: PositionPostingRepository):
        self.repository = repository

    def get_form_state(self, user: User) -> PositionPostingFormState:
        company_rep = self._require_company_rep(user)
        company = self.repository.get_company(company_rep.companyID)
        cycle = self.repository.get_current_cycle()
        if company is None:
            raise NotACompanyRepError
        if (
            cycle is None
            or cycle.cycleID is None
            or cycle.status.strip().casefold() != "open"
        ):
            raise CycleClosedError
        return PositionPostingFormState(
            company=company,
            cycle=cycle,
            available_skills=self.repository.get_all_skills(),
        )

    def create_position(
        self,
        user: User,
        title: str,
        description: str,
        skill_ids: list[int],
    ) -> Position:
        company_rep = self._require_company_rep(user)
        cycle = self.repository.get_current_cycle()
        if (
            cycle is None
            or cycle.cycleID is None
            or cycle.status.strip().casefold() != "open"
        ):
            raise CycleClosedError

        clean_title = title.strip()
        clean_description = description.strip()
        if not clean_title:
            raise InvalidTitleInputError
        if not clean_description:
            raise InvalidDescriptionInputError
        if (
            not skill_ids
            or len(set(skill_ids)) != len(skill_ids)
            or len(self.repository.get_skills_by_ids(skill_ids)) != len(skill_ids)
        ):
            raise InvalidSkillInputError

        position = Position(
            companyID=company_rep.companyID,
            cycleID=cycle.cycleID,
            title=clean_title,
            description=clean_description,
            dateOpened=date.today(),
            status="open",
        )
        return self.repository.create_position(position, skill_ids)

    def _require_company_rep(self, user: User) -> CompanyRep:
        if user.role.strip().casefold() != "company_rep" or user.id is None:
            raise NotACompanyRepError
        company_rep = self.repository.get_company_rep_for_user(user.id)
        if company_rep is None:
            raise NotACompanyRepError
        return company_rep
