from dataclasses import dataclass
from datetime import date

from sqlalchemy.exc import IntegrityError

from app.models.application import Application, InternshipCycle, Skill, Student
from app.models.position import Company, Match, Position
from app.models.user import User
from app.repositories.matching import MatchingRepository
from app.services.application_service import CycleClosedError


class MatchingError(Exception):
    pass


class NotCoordinatorError(MatchingError):
    pass


class ApplicationAlreadyPlacedError(MatchingError):
    pass


class PositionNotOpenError(MatchingError):
    pass


class PairAlreadyMatchedError(MatchingError):
    pass


class ApplicationNotFoundError(MatchingError):
    pass


class PositionNotFoundError(MatchingError):
    pass


class InvalidApplicationFilterError(MatchingError):
    pass


@dataclass(frozen=True)
class PositionOption:
    position: Position
    company: Company
    fit_percentage: float
    matched_skills: list[Skill]
    missing_skills: list[Skill]


@dataclass(frozen=True)
class CurrentMatch:
    match: Match
    position: Position
    company: Company


@dataclass(frozen=True)
class CoordinatorApplicationRow:
    application: Application
    student: Student
    student_user: User
    active_match_count: int


@dataclass(frozen=True)
class CoordinatorDashboardState:
    cycle: InternshipCycle | None
    cycle_is_open: bool
    applications_to_mark_not_matched: int
    applications: list[CoordinatorApplicationRow]
    status_filter: str
    search_query: str
    filter_counts: dict[str, int]
    filters: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class MatchingPageState:
    application: Application
    student: Student
    student_user: User
    student_skills: list[Skill]
    cycle: InternshipCycle | None
    cycle_is_open: bool
    has_open_positions: bool
    can_match: bool
    suggested_positions: list[PositionOption]
    open_positions: list[PositionOption]
    current_matches: list[CurrentMatch]


class MatchingService:
    FILTERS = (
        ("all", "All"),
        ("matched", "Matched"),
        ("placed", "Placed"),
        ("awaiting_rematch", "Awaiting rematch"),
        ("submitted", "Submitted"),
    )
    CLOSED_CYCLE_FILTERS = (
        ("all", "All"),
        ("matched", "Matched"),
        ("placed", "Placed"),
        ("not_matched", "Not Matched"),
    )

    def __init__(self, matching_repository: MatchingRepository):
        self.matching_repository = matching_repository

    def get_coordinator_dashboard_state(
        self,
        user: User,
        status_filter: str = "all",
        search_query: str = "",
    ) -> CoordinatorDashboardState:
        self._require_coordinator(user)
        cycle = self.matching_repository.get_current_cycle()
        cycle_is_open = cycle is not None and cycle.status.casefold() == "open"
        filters = self.FILTERS if cycle_is_open else self.CLOSED_CYCLE_FILTERS
        normalized_filter = status_filter.strip().casefold().replace("_", " ")
        valid_filters = {value.replace("_", " ") for value, _ in filters}
        if normalized_filter not in valid_filters:
            raise InvalidApplicationFilterError
        normalized_search = search_query.strip().casefold()

        application_rows: list[CoordinatorApplicationRow] = []
        applications_to_mark_not_matched = 0
        records: list[tuple[Application, Student, User]] = []
        application_status_counts: dict[str, int] = {}
        if cycle is not None and cycle.cycleID is not None:
            active_match_counts = self.matching_repository.get_active_match_counts(
                cycle.cycleID
            )
            records = self.matching_repository.get_applications_for_cycle(
                cycle.cycleID
            )
            applications_to_mark_not_matched = sum(
                1
                for application, _, _ in records
                if application.status.strip().casefold().replace("_", " ")
                in {"submitted", "awaiting rematch"}
                and active_match_counts.get(application.applicationID, 0) == 0
            )
            for application, student, student_user in records:
                normalized_status = (
                    application.status.strip().casefold().replace("_", " ")
                )
                application_status_counts[normalized_status] = (
                    application_status_counts.get(normalized_status, 0) + 1
                )
                if (
                    normalized_filter != "all"
                    and normalized_status != normalized_filter
                ):
                    continue
                student_name = (
                    student_user.fullName or student_user.username
                ).casefold()
                student_id = str(student.studentID)
                if normalized_search and (
                    normalized_search not in student_name
                    and normalized_search not in student_id
                ):
                    continue
                application_rows.append(
                    CoordinatorApplicationRow(
                        application=application,
                        student=student,
                        student_user=student_user,
                        active_match_count=active_match_counts.get(
                            application.applicationID,
                            0,
                        ),
                    )
                )

        filter_counts = {
            filter_key: (
                len(records)
                if filter_key == "all"
                else application_status_counts.get(
                    filter_key.replace("_", " "),
                    0,
                )
            )
            for filter_key, _ in filters
        }
        return CoordinatorDashboardState(
            cycle=cycle,
            cycle_is_open=cycle_is_open,
            applications_to_mark_not_matched=applications_to_mark_not_matched,
            applications=application_rows,
            status_filter=normalized_filter.replace(" ", "_"),
            search_query=search_query.strip(),
            filter_counts=filter_counts,
            filters=filters,
        )

    def get_matching_page_state(
        self,
        user: User,
        application_id: int,
    ) -> MatchingPageState:
        self._require_coordinator(user)
        application = self.matching_repository.get_application(application_id)
        if application is None:
            raise ApplicationNotFoundError

        student = self.matching_repository.get_student(application.studentID)
        if student is None:
            raise ApplicationNotFoundError
        student_user = self.matching_repository.get_user(student.userID)
        if student_user is None:
            raise ApplicationNotFoundError

        cycle = self.matching_repository.get_cycle(application.cycleID)
        cycle_is_open = cycle is not None and cycle.status.casefold() == "open"
        application_is_placed = application.status.casefold() == "placed"
        current_match_records = self.matching_repository.get_current_matches(
            application_id
        )
        matched_position_ids = {
            position.positionID
            for _, position, _ in current_match_records
        }

        open_position_records = (
            self.matching_repository.get_open_positions_for_cycle(cycle.cycleID)
            if cycle is not None and cycle.cycleID is not None
            else []
        )
        eligible_records = [
            (position, company)
            for position, company in open_position_records
            if position.positionID not in matched_position_ids
        ]
        position_ids = [
            position.positionID
            for position, _ in eligible_records
            if position.positionID is not None
        ]
        required_skills = self.matching_repository.get_required_skills(position_ids)
        student_skills = self.matching_repository.get_student_skills(
            student.studentID
        )
        student_skill_ids = {
            skill.skillID for skill in student_skills if skill.skillID is not None
        }

        open_positions = []
        for position, company in eligible_records:
            position_id = position.positionID
            position_skills = required_skills.get(position_id, [])
            required_ids = {
                skill.skillID
                for skill in position_skills
                if skill.skillID is not None
            }
            matched_skills = [
                skill
                for skill in position_skills
                if skill.skillID in student_skill_ids
            ]
            missing_skills = [
                skill
                for skill in position_skills
                if skill.skillID not in student_skill_ids
            ]
            fit_percentage = (
                len(student_skill_ids.intersection(required_ids))
                / len(required_ids)
                * 100
                if required_ids
                else 0.0
            )
            open_positions.append(
                PositionOption(
                    position=position,
                    company=company,
                    fit_percentage=fit_percentage,
                    matched_skills=matched_skills,
                    missing_skills=missing_skills,
                )
            )
        open_positions.sort(
            key=lambda option: (
                -option.fit_percentage,
                option.position.title.casefold(),
                option.company.name.casefold(),
                option.position.positionID or 0,
            )
        )

        can_match = cycle_is_open and not application_is_placed
        suggested_positions = (
            [
                option
                for option in open_positions
                if option.fit_percentage > 0
            ][:3]
            if can_match
            else []
        )
        suggested_position_ids = {
            option.position.positionID for option in suggested_positions
        }
        remaining_open_positions = [
            option
            for option in open_positions
            if option.position.positionID not in suggested_position_ids
        ]
        current_matches = [
            CurrentMatch(match=match, position=position, company=company)
            for match, position, company in current_match_records
        ]
        return MatchingPageState(
            application=application,
            student=student,
            student_user=student_user,
            student_skills=student_skills,
            cycle=cycle,
            cycle_is_open=cycle_is_open,
            has_open_positions=bool(open_position_records),
            can_match=can_match,
            suggested_positions=suggested_positions,
            open_positions=remaining_open_positions,
            current_matches=current_matches,
        )

    def submit_match(
        self,
        user: User,
        application_id: int,
        position_id: int,
    ) -> Match:
        self._require_coordinator(user)
        application = self.matching_repository.get_application(application_id)
        if application is None:
            raise ApplicationNotFoundError
        position = self.matching_repository.get_position(position_id)
        if position is None:
            raise PositionNotFoundError
        if application.status.casefold() == "placed":
            raise ApplicationAlreadyPlacedError

        cycle = self.matching_repository.get_cycle(application.cycleID)
        if cycle is None or cycle.status.casefold() != "open":
            raise CycleClosedError
        if (
            position.status.casefold() != "open"
            or position.cycleID != application.cycleID
        ):
            raise PositionNotOpenError
        if self.matching_repository.has_match(application_id, position_id):
            raise PairAlreadyMatchedError

        match = Match(
            applicationID=application_id,
            positionID=position_id,
            matchDate=date.today(),
            status="matched",
        )
        if application.status.casefold() != "matched":
            application.status = "matched"
        try:
            return self.matching_repository.create_match(application, match)
        except IntegrityError as exc:
            if self.matching_repository.has_match(application_id, position_id):
                raise PairAlreadyMatchedError from exc
            raise

    @staticmethod
    def _require_coordinator(user: User) -> None:
        if user.role.strip().casefold() != "coordinator":
            raise NotCoordinatorError
