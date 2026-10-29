from datetime import date, timedelta
import unittest

import pytest
from sqlmodel import select

from app.models.application import Application, InternshipCycle
from app.models.position import Company, CompanyRep, Match, Position
from app.models.user import UserBase
from app.repositories.application import ApplicationRepository
from app.repositories.candidate_selection import CandidateSelectionRepository
from app.repositories.cycle_closure import CycleClosureRepository
from app.repositories.matching import MatchingRepository
from app.repositories.position_posting import PositionPostingRepository
from app.repositories.user import UserRepository
from app.services.application_service import ApplicationService, CycleClosedError
from app.services.auth_service import AuthService
from app.services.candidate_selection_service import CandidateSelectionService
from app.services.cycle_closure_service import CycleClosureService
from app.services.matching_service import MatchingService
from app.services.position_posting_service import PositionPostingService


class CycleClosureIntegrationTests(unittest.TestCase):
    def _create_student_application(self, username, student_id):
        user = AuthService(UserRepository(self.session)).register_user(
            username=username,
            email=f"{username}@example.com",
            password="secure-password",
            full_name=username.replace("-", " ").title(),
            number="868-555-0113",
        )
        application = ApplicationService(
            ApplicationRepository(self.session)
        ).submit_application(
            user=user,
            student_id=student_id,
            gpa=3.5,
            degree_name="Computer Science",
            expected_graduation_date=date.today() + timedelta(days=365),
            resume_link="https://example.com/resume",
            skill_ids=[1, 2],
        )
        return user, application

    def _create_company_rep(self):
        company = Company(name="Cycle Company", location="Arima")
        self.session.add(company)
        self.session.flush()
        rep = UserRepository(self.session).create(
            UserBase(
                username="cycle-rep",
                email="cycle-rep@example.com",
                fullName="Cycle Representative",
                number="868-555-0114",
                password="stored-password",
                role="company_rep",
            )
        )
        coordinator = UserRepository(self.session).create(
            UserBase(
                username="cycle-coordinator",
                email="cycle-coordinator@example.com",
                fullName="Cycle Coordinator",
                number="868-555-0115",
                password="stored-password",
                role="coordinator",
            )
        )
        self.assertIsNotNone(company.companyID)
        self.assertIsNotNone(rep)
        self.assertIsNotNone(rep.id)
        self.assertIsNotNone(coordinator)
        self.session.add(CompanyRep(userID=rep.id, companyID=company.companyID))
        self.session.commit()
        return rep, coordinator

    def _create_position(self, rep, title):
        return PositionPostingService(
            PositionPostingRepository(self.session)
        ).create_position(
            user=rep,
            title=title,
            description="Support the team",
            skill_ids=[1, 2],
        )

    def test_close_cycle(self):
        _, submitted_application = self._create_student_application(
            "cycle-student-one",
            4001,
        )
        _, awaiting_application = self._create_student_application(
            "cycle-student-two",
            4002,
        )
        _, matched_application = self._create_student_application(
            "cycle-student-three",
            4003,
        )
        rep, coordinator = self._create_company_rep()
        rejected_position = self._create_position(rep, "Rejected Candidate Intern")
        matched_position = self._create_position(rep, "Matched Candidate Intern")
        matching_service = MatchingService(MatchingRepository(self.session))
        rejected_match = matching_service.submit_match(
            coordinator,
            awaiting_application.applicationID,
            rejected_position.positionID,
        )
        matching_service.submit_match(
            coordinator,
            matched_application.applicationID,
            matched_position.positionID,
        )
        CandidateSelectionService(
            CandidateSelectionRepository(self.session)
        ).process_company_action(rep, rejected_match.matchID, "reject")

        updated_count = CycleClosureService(
            CycleClosureRepository(self.session)
        ).close_cycle(coordinator)

        self.session.expire_all()
        saved_cycle = self.session.get(InternshipCycle, 1)
        saved_submitted_application = self.session.get(
            Application,
            submitted_application.applicationID,
        )
        saved_awaiting_application = self.session.get(
            Application,
            awaiting_application.applicationID,
        )
        saved_matched_application = self.session.get(
            Application,
            matched_application.applicationID,
        )
        saved_positions = self.session.exec(
            select(Position).where(Position.cycleID == 1)
        ).all()
        saved_matched_records = self.session.exec(
            select(Match).where(
                Match.applicationID == matched_application.applicationID
            )
        ).all()

        self.assertEqual(updated_count, 2)
        self.assertEqual(saved_cycle.status, "closed")
        self.assertEqual(saved_submitted_application.status, "not matched")
        self.assertEqual(saved_awaiting_application.status, "not matched")
        self.assertEqual(saved_matched_application.status, "matched")
        self.assertEqual(
            {position.status for position in saved_positions},
            {"closed"},
        )
        self.assertEqual(saved_matched_records[0].status, "matched")

    def test_closed_cycle_blocks_new_work(self):
        _, existing_application = self._create_student_application(
            "cycle-student-four",
            4004,
        )
        _, unmatched_application = self._create_student_application(
            "cycle-student-five",
            4005,
        )
        rep, coordinator = self._create_company_rep()
        position = self._create_position(rep, "Existing Match Intern")
        match = MatchingService(MatchingRepository(self.session)).submit_match(
            coordinator,
            existing_application.applicationID,
            position.positionID,
        )
        CycleClosureService(CycleClosureRepository(self.session)).close_cycle(
            coordinator
        )

        with pytest.raises(CycleClosedError):
            MatchingService(MatchingRepository(self.session)).submit_match(
                coordinator,
                unmatched_application.applicationID,
                position.positionID,
            )

        with pytest.raises(CycleClosedError):
            PositionPostingService(
                PositionPostingRepository(self.session)
            ).create_position(
                user=rep,
                title="Too Late Intern",
                description="This must be blocked",
                skill_ids=[1],
            )

        CandidateSelectionService(
            CandidateSelectionRepository(self.session)
        ).process_company_action(rep, match.matchID, "interview")

        self.session.expire_all()
        saved_match = self.session.get(Match, match.matchID)
        saved_position = self.session.get(Position, position.positionID)
        saved_cycle = self.session.get(InternshipCycle, 1)

        self.assertEqual(saved_match.status, "interviewing")
        self.assertEqual(saved_position.status, "closed")
        self.assertEqual(saved_cycle.status, "closed")
