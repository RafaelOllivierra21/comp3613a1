from dataclasses import dataclass, field

from app.models.application import Application, Student
from app.models.position import Company, CompanyRep, Match, Position
from app.models.user import User
from app.repositories.candidate_selection import (
    ACTIVE_MATCH_STATUSES,
    CandidateSelectionRepository,
)
from app.services.application_service import NotAStudentError


class CandidateSelectionError(Exception):
    pass


class NotACompanyRepError(CandidateSelectionError):
    pass


class MatchIDNotFoundError(CandidateSelectionError):
    pass


class MatchNotInCompanyError(CandidateSelectionError):
    pass


class InvalidActionError(CandidateSelectionError):
    pass


class OfferAlreadyPendingError(CandidateSelectionError):
    pass


class MatchNotInStudentError(CandidateSelectionError):
    pass


@dataclass(frozen=True)
class StudentMatchCard:
    match: Match
    position: Position
    company: Company


@dataclass
class CompanyPositionCard:
    position: Position
    candidates: list["CompanyCandidateCard"] = field(default_factory=list)
    offer_pending: bool = False


@dataclass(frozen=True)
class CompanyCandidateCard:
    match: Match
    application: Application
    student: Student
    student_user: User


@dataclass(frozen=True)
class CompanyRepDashboardState:
    positions: list[CompanyPositionCard]


class CandidateSelectionService:
    def __init__(self, candidate_selection_repository: CandidateSelectionRepository):
        self.candidate_selection_repository = candidate_selection_repository

    def get_company_rep_dashboard_state(
        self,
        user: User,
    ) -> CompanyRepDashboardState:
        company_rep = self._require_company_rep(user)
        positions = self.candidate_selection_repository.get_company_positions(
            company_rep.companyID
        )
        position_cards = {
            position.positionID: CompanyPositionCard(position=position)
            for position in positions
        }
        for match, application, student, student_user, position in (
            self.candidate_selection_repository.get_company_candidate_records(
                company_rep.companyID
            )
        ):
            card = position_cards.get(position.positionID)
            if card is not None:
                card.candidates.append(
                    CompanyCandidateCard(
                        match=match,
                        application=application,
                        student=student,
                        student_user=student_user,
                    )
                )
        for card in position_cards.values():
            card.offer_pending = any(
                self._normalize_status(candidate.match.status) == "offered"
                for candidate in card.candidates
            )
        return CompanyRepDashboardState(positions=list(position_cards.values()))

    def get_student_matches(self, user: User) -> list[StudentMatchCard]:
        self._require_student(user)
        if user.id is None:
            return []
        student = self.candidate_selection_repository.get_student_for_user(user.id)
        cycle = self.candidate_selection_repository.get_current_cycle()
        if student is None or cycle is None or cycle.cycleID is None:
            return []
        application = self.candidate_selection_repository.get_application_for_student_cycle(
            student.studentID,
            cycle.cycleID,
        )
        if application is None or application.applicationID is None:
            return []
        return [
            StudentMatchCard(match=match, position=position, company=company)
            for match, position, company in (
                self.candidate_selection_repository.get_student_match_records(
                    application.applicationID
                )
            )
        ]

    def process_company_action(
        self,
        user: User,
        match_id: int,
        action: str,
    ) -> None:
        company_rep = self._require_company_rep(user)
        match = self.candidate_selection_repository.get_match(match_id)
        if match is None:
            raise MatchIDNotFoundError

        position = self.candidate_selection_repository.get_position(match.positionID)
        if position is None or position.companyID != company_rep.companyID:
            raise MatchNotInCompanyError
        action = action.strip().casefold()
        current_status = self._normalize_status(match.status)

        if action == "interview" and current_status == "matched":
            match.status = "interviewing"
        elif action == "offer" and current_status == "interviewing":
            if self.candidate_selection_repository.has_pending_offer(
                position.positionID,
                match_id,
            ):
                raise OfferAlreadyPendingError
            match.status = "offered"
        elif action == "reject" and current_status in {"matched", "interviewing"}:
            match.status = "rejected by company"
            application = self.candidate_selection_repository.get_application(
                match.applicationID
            )
            if application is None:
                raise MatchIDNotFoundError
            self._refresh_unmatched_application_status(application)
        else:
            raise InvalidActionError

        self.candidate_selection_repository.save_changes()

    def process_student_action(
        self,
        user: User,
        match_id: int,
        action: str,
    ) -> None:
        self._require_student(user)
        if user.id is None:
            raise MatchNotInStudentError
        match = self.candidate_selection_repository.get_match(match_id)
        if match is None:
            raise MatchIDNotFoundError
        student = self.candidate_selection_repository.get_student_for_user(user.id)
        application = self.candidate_selection_repository.get_application(
            match.applicationID
        )
        if (
            student is None
            or application is None
            or application.studentID != student.studentID
        ):
            raise MatchNotInStudentError
        if self._normalize_status(match.status) != "offered":
            raise InvalidActionError

        action = action.strip().casefold()
        if action == "decline":
            match.status = "declined by student"
            self._refresh_unmatched_application_status(application)
        elif action == "accept":
            position = self.candidate_selection_repository.get_position(
                match.positionID
            )
            if position is None:
                raise MatchIDNotFoundError
            match.status = "accepted"
            position.status = "filled"
            application.status = "placed"
            self._close_matches_for_placed_student(application.applicationID, match_id)
            self._close_matches_for_filled_position(
                position.positionID,
                application.applicationID,
                match_id,
            )
        else:
            raise InvalidActionError

        self.candidate_selection_repository.save_changes()

    def _close_matches_for_placed_student(
        self,
        application_id: int,
        accepted_match_id: int,
    ) -> None:
        for match in self.candidate_selection_repository.get_matches_for_application(
            application_id
        ):
            if (
                match.matchID != accepted_match_id
                and self._normalize_status(match.status) in ACTIVE_MATCH_STATUSES
            ):
                match.status = "closed - student placed elsewhere"

    def _close_matches_for_filled_position(
        self,
        position_id: int,
        placed_application_id: int,
        accepted_match_id: int,
    ) -> None:
        candidate_application_ids: set[int] = set()
        for match in self.candidate_selection_repository.get_matches_for_position(
            position_id
        ):
            if (
                match.matchID != accepted_match_id
                and match.applicationID != placed_application_id
                and self._normalize_status(match.status) in ACTIVE_MATCH_STATUSES
            ):
                match.status = "closed - position filled"
                candidate_application_ids.add(match.applicationID)
        for application_id in candidate_application_ids:
            application = self.candidate_selection_repository.get_application(
                application_id
            )
            if application is not None:
                self._refresh_unmatched_application_status(application)

    def _refresh_unmatched_application_status(
        self,
        application: Application,
    ) -> None:
        if self.candidate_selection_repository.has_active_matches(
            application.applicationID
        ):
            return
        cycle = self.candidate_selection_repository.get_cycle(application.cycleID)
        application.status = (
            "awaiting rematch"
            if cycle is not None and cycle.status.casefold() == "open"
            else "not matched"
        )

    def _require_company_rep(self, user: User) -> CompanyRep:
        if user.role.strip().casefold() != "company_rep" or user.id is None:
            raise NotACompanyRepError
        company_rep = self.candidate_selection_repository.get_company_rep_for_user(
            user.id
        )
        if company_rep is None:
            raise NotACompanyRepError
        return company_rep

    @staticmethod
    def _require_student(user: User) -> None:
        if user.role.strip().casefold() != "student":
            raise NotAStudentError

    @staticmethod
    def _normalize_status(status: str) -> str:
        return " ".join(status.replace("_", " ").replace("-", " ").split()).casefold()
