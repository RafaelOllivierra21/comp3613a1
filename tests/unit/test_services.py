from datetime import date
from unittest.mock import MagicMock
import unittest

import pytest

from app.models.application import Application, InternshipCycle, Skill, Student
from app.models.position import Company, CompanyRep, Match, Position
from app.models.user import User
from app.services.application_service import (
    ApplicationService,
    CycleClosedError,
    InvalidGPAInputError,
    NotAStudentError,
)
from app.services.auth_service import AuthService
from app.services.candidate_selection_service import (
    CandidateSelectionService,
    InvalidActionError,
    OfferAlreadyPendingError,
)
from app.services.cycle_closure_service import (
    CycleClosureService,
)
from app.services.matching_service import MatchingService
from app.services.matching_service import NotCoordinatorError
from app.services.position_posting_service import (
    InvalidTitleInputError,
    PositionPostingService,
)
from app.utilities.security import encrypt_password


def _user(role: str, user_id: int = 1) -> User:
    return User(
        id=user_id,
        username="bob",
        email="bob@mail.com",
        fullName="Bob Smith",
        number="868-555-0101",
        password="hashed-password",
        role=role,
    )


def _matching_state(positions: list[Position], required: dict[int, list[Skill]], student_skills: list[Skill]):
    repository = MagicMock()
    repository.get_application.return_value = Application(
        applicationID=1,
        studentID=1,
        cycleID=1,
        dateSubmitted=date.today(),
        status="submitted",
    )
    repository.get_student.return_value = Student(
        studentID=1,
        userID=1,
        gpa=3.5,
        degreeName="Computer Science",
        expectedGraduationDate=date(2027, 5, 1),
        resumeLink="https://example.com/resume",
    )
    repository.get_user.return_value = _user("student")
    repository.get_cycle.return_value = InternshipCycle(
        cycleID=1,
        startDate=date(2026, 1, 1),
        endDate=date(2026, 12, 31),
        status="open",
    )
    repository.get_current_matches.return_value = []
    repository.get_open_positions_for_cycle.return_value = [
        (
            position,
            Company(companyID=position.companyID, name="Example Co", location="Port of Spain"),
        )
        for position in positions
    ]
    repository.get_required_skills.return_value = required
    repository.get_student_skills.return_value = student_skills
    return repository


class ServiceUnitTests(unittest.TestCase):
    def test_authenticate_bad_password(self):
        repository = MagicMock()
        repository.get_by_username.return_value = User(
            id=1,
            username="bob",
            email="bob@mail.com",
            fullName="Bob Smith",
            number="868-555-0101",
            password=encrypt_password("mypass"),
            role="student",
        )

        assert AuthService(repository).authenticate_user("bob", "wrong") is None


    def test_apply_not_student(self):
        repository = MagicMock()
        service = ApplicationService(repository)

        with pytest.raises(NotAStudentError):
            service.submit_application(
                user=_user("company_rep"),
                student_id=1001,
                gpa=3.5,
                degree_name="Computer Science",
                expected_graduation_date=date(2027, 5, 1),
                resume_link="https://example.com/resume",
                skill_ids=[1],
            )


    def test_apply_cycle_closed(self):
        repository = MagicMock()
        repository.get_current_cycle.return_value = InternshipCycle(
            cycleID=1,
            startDate=date(2026, 1, 1),
            endDate=date(2026, 12, 31),
            status="closed",
        )
        service = ApplicationService(repository)

        with pytest.raises(CycleClosedError):
            service.submit_application(
                user=_user("student"),
                student_id=1001,
                gpa=3.5,
                degree_name="Computer Science",
                expected_graduation_date=date(2027, 5, 1),
                resume_link="https://example.com/resume",
                skill_ids=[1],
            )


    def test_apply_invalid_gpa(self):
        repository = MagicMock()
        repository.get_current_cycle.return_value = InternshipCycle(
            cycleID=1,
            startDate=date(2026, 1, 1),
            endDate=date(2026, 12, 31),
            status="open",
        )
        repository.get_application_for_user_cycle.return_value = None
        repository.get_student_by_id.return_value = None
        service = ApplicationService(repository)

        with pytest.raises(InvalidGPAInputError):
            service.submit_application(
                user=_user("student"),
                student_id=1001,
                gpa=5.0,
                degree_name="Computer Science",
                expected_graduation_date=date(2027, 5, 1),
                resume_link="https://example.com/resume",
                skill_ids=[1],
            )


    def test_fit_percentage(self):
        required_skills = [
            Skill(skillID=1, name="Python"),
            Skill(skillID=2, name="SQL"),
            Skill(skillID=3, name="Testing"),
        ]
        position = Position(
            positionID=1,
            companyID=1,
            cycleID=1,
            title="IT Intern",
            description="Support desk",
            dateOpened=date.today(),
            status="open",
        )
        repository = _matching_state(
            [position],
            {1: required_skills},
            required_skills[:2],
        )

        state = MatchingService(repository).get_matching_page_state(
            _user("coordinator"),
            application_id=1,
        )

        assert state.suggested_positions[0].fit_percentage == pytest.approx(66.67, abs=0.01)


    def test_suggestions_top_three(self):
        student_skills = [Skill(skillID=1, name="Python"), Skill(skillID=2, name="SQL")]
        skill_pool = [Skill(skillID=index, name=f"Skill {index}") for index in range(1, 7)]
        specifications = [
            ("Position 100", [1, 2]),
            ("Position 67", [1, 2, 3]),
            ("Position 50", [1, 2, 3, 4]),
            ("Position 33", [1, 2, 3, 4, 5, 6]),
            ("Position 0", [3, 4]),
        ]
        positions = [
            Position(
                positionID=index,
                companyID=1,
                cycleID=1,
                title=title,
                description="Internship",
                dateOpened=date.today(),
                status="open",
            )
            for index, (title, _) in enumerate(specifications, start=1)
        ]
        required = {
            position.positionID: [skill_pool[skill_id - 1] for skill_id in skill_ids]
            for position, (_, skill_ids) in zip(positions, specifications)
        }
        repository = _matching_state(positions, required, student_skills)

        state = MatchingService(repository).get_matching_page_state(
            _user("coordinator"),
            application_id=1,
        )

        assert len(state.suggested_positions) == 3
        assert [option.position.title for option in state.suggested_positions] == [
            "Position 100",
            "Position 67",
            "Position 50",
        ]


    def test_suggestion_tiebreak(self):
        skill = Skill(skillID=1, name="Python")
        positions = [
            Position(
                positionID=index,
                companyID=1,
                cycleID=1,
                title=title,
                description="Internship",
                dateOpened=date.today(),
                status="open",
            )
            for index, title in enumerate(("Law Intern", "IT Intern"), start=1)
        ]
        repository = _matching_state(
            positions,
            {position.positionID: [skill, Skill(skillID=2, name="SQL")] for position in positions},
            [skill],
        )

        state = MatchingService(repository).get_matching_page_state(
            _user("coordinator"),
            application_id=1,
        )

        assert [option.position.title for option in state.suggested_positions] == [
            "IT Intern",
            "Law Intern",
        ]


    def test_offer_before_interview(self):
        repository = MagicMock()
        repository.get_company_rep_for_user.return_value = CompanyRep(
            repID=1,
            userID=1,
            companyID=1,
        )
        repository.get_match.return_value = Match(
            matchID=1,
            applicationID=1,
            positionID=1,
            matchDate=date.today(),
            status="matched",
        )
        repository.get_position.return_value = Position(
            positionID=1,
            companyID=1,
            cycleID=1,
            title="IT Intern",
            description="Support desk",
            dateOpened=date.today(),
            status="open",
        )
        service = CandidateSelectionService(repository)

        with pytest.raises(InvalidActionError):
            service.process_company_action(
                user=_user("company_rep"),
                match_id=1,
                action="offer",
            )


    def test_offer_already_pending(self):
        repository = MagicMock()
        repository.get_company_rep_for_user.return_value = CompanyRep(
            repID=1,
            userID=1,
            companyID=1,
        )
        repository.get_match.return_value = Match(
            matchID=1,
            applicationID=1,
            positionID=1,
            matchDate=date.today(),
            status="interviewing",
        )
        repository.get_position.return_value = Position(
            positionID=1,
            companyID=1,
            cycleID=1,
            title="IT Intern",
            description="Support desk",
            dateOpened=date.today(),
            status="open",
        )
        repository.has_pending_offer.return_value = True
        service = CandidateSelectionService(repository)

        with pytest.raises(OfferAlreadyPendingError):
            service.process_company_action(
                user=_user("company_rep"),
                match_id=1,
                action="offer",
            )


    def test_post_position_blank_title(self):
        repository = MagicMock()
        repository.get_company_rep_for_user.return_value = CompanyRep(
            repID=1,
            userID=1,
            companyID=1,
        )
        repository.get_current_cycle.return_value = InternshipCycle(
            cycleID=1,
            startDate=date(2026, 1, 1),
            endDate=date(2026, 12, 31),
            status="open",
        )
        service = PositionPostingService(repository)

        with pytest.raises(InvalidTitleInputError):
            service.create_position(
                user=_user("company_rep"),
                title="   ",
                description="Support desk",
                skill_ids=[1],
            )


    def test_close_cycle_not_coordinator(self):
        repository = MagicMock()
        service = CycleClosureService(repository)

        with pytest.raises(NotCoordinatorError):
            service.close_cycle(_user("student"))
