from datetime import date, timedelta
import unittest

from app.models.application import Application
from app.models.position import Company, CompanyRep, Match, Position
from app.models.user import UserBase
from app.repositories.application import ApplicationRepository
from app.repositories.candidate_selection import CandidateSelectionRepository
from app.repositories.matching import MatchingRepository
from app.repositories.position_posting import PositionPostingRepository
from app.repositories.user import UserRepository
from app.services.application_service import ApplicationService
from app.services.auth_service import AuthService
from app.services.candidate_selection_service import CandidateSelectionService
from app.services.matching_service import MatchingService
from app.services.position_posting_service import PositionPostingService


class CandidateSelectionIntegrationTests(unittest.TestCase):
    def _create_student_application(self, username, student_id):
        user = AuthService(UserRepository(self.session)).register_user(
            username=username,
            email=f"{username}@example.com",
            password="secure-password",
            full_name=username.replace("-", " ").title(),
            number="868-555-0110",
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
        company = Company(name="Selection Company", location="Chaguanas")
        self.session.add(company)
        self.session.flush()
        rep = UserRepository(self.session).create(
            UserBase(
                username="selection-rep",
                email="selection-rep@example.com",
                fullName="Selection Representative",
                number="868-555-0111",
                password="stored-password",
                role="company_rep",
            )
        )
        coordinator = UserRepository(self.session).create(
            UserBase(
                username="selection-coordinator",
                email="selection-coordinator@example.com",
                fullName="Selection Coordinator",
                number="868-555-0112",
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

    def _submit_match(self, coordinator, application, position):
        return MatchingService(MatchingRepository(self.session)).submit_match(
            user=coordinator,
            application_id=application.applicationID,
            position_id=position.positionID,
        )

    def test_interview_and_offer(self):
        student, application = self._create_student_application(
            "selection-student-one",
            3001,
        )
        rep, coordinator = self._create_company_rep()
        position = self._create_position(rep, "Interview Intern")
        match = self._submit_match(coordinator, application, position)
        service = CandidateSelectionService(CandidateSelectionRepository(self.session))

        service.process_company_action(rep, match.matchID, "interview")
        self.session.expire_all()
        interviewing_match = CandidateSelectionRepository(self.session).get_match(
            match.matchID
        )
        self.assertEqual(interviewing_match.status, "interviewing")

        service.process_company_action(rep, match.matchID, "offer")
        self.session.expire_all()
        offered_match = CandidateSelectionRepository(self.session).get_match(
            match.matchID
        )

        self.assertEqual(offered_match.status, "offered")
        self.assertIsNotNone(student.id)

    def test_reject_last_match(self):
        _, application = self._create_student_application(
            "selection-student-two",
            3002,
        )
        rep, coordinator = self._create_company_rep()
        position = self._create_position(rep, "Rejection Intern")
        match = self._submit_match(coordinator, application, position)

        CandidateSelectionService(
            CandidateSelectionRepository(self.session)
        ).process_company_action(rep, match.matchID, "reject")

        self.session.expire_all()
        repository = CandidateSelectionRepository(self.session)
        saved_match = repository.get_match(match.matchID)
        saved_application = repository.get_application(application.applicationID)

        self.assertEqual(saved_match.status, "rejected by company")
        self.assertEqual(saved_application.status, "awaiting rematch")

    def test_accept_offer(self):
        student, application = self._create_student_application(
            "selection-student-three",
            3003,
        )
        _, other_application = self._create_student_application(
            "selection-student-four",
            3004,
        )
        rep, coordinator = self._create_company_rep()
        accepted_position = self._create_position(rep, "Accepted Intern")
        other_position = self._create_position(rep, "Alternate Intern")
        accepted_match = self._submit_match(
            coordinator,
            application,
            accepted_position,
        )
        student_other_match = self._submit_match(
            coordinator,
            application,
            other_position,
        )
        other_candidate_match = self._submit_match(
            coordinator,
            other_application,
            accepted_position,
        )
        service = CandidateSelectionService(CandidateSelectionRepository(self.session))
        service.process_company_action(rep, accepted_match.matchID, "interview")
        service.process_company_action(rep, accepted_match.matchID, "offer")

        service.process_student_action(student, accepted_match.matchID, "accept")

        self.session.expire_all()
        saved_match = self.session.get(Match, accepted_match.matchID)
        saved_student_other_match = self.session.get(Match, student_other_match.matchID)
        saved_other_candidate_match = self.session.get(
            Match,
            other_candidate_match.matchID,
        )
        saved_application = self.session.get(Application, application.applicationID)
        saved_other_application = self.session.get(
            Application,
            other_application.applicationID,
        )
        saved_position = self.session.get(Position, accepted_position.positionID)

        self.assertEqual(saved_match.status, "accepted")
        self.assertEqual(saved_application.status, "placed")
        self.assertEqual(saved_position.status, "filled")
        self.assertEqual(
            saved_student_other_match.status,
            "closed - student placed elsewhere",
        )
        self.assertEqual(
            saved_other_candidate_match.status,
            "closed - position filled",
        )
        self.assertEqual(saved_other_application.status, "awaiting rematch")

    def test_decline_offer(self):
        first_student, first_application = self._create_student_application(
            "selection-student-five",
            3005,
        )
        _, second_application = self._create_student_application(
            "selection-student-six",
            3006,
        )
        rep, coordinator = self._create_company_rep()
        position = self._create_position(rep, "Decline Intern")
        first_match = self._submit_match(
            coordinator,
            first_application,
            position,
        )
        second_match = self._submit_match(
            coordinator,
            second_application,
            position,
        )
        service = CandidateSelectionService(CandidateSelectionRepository(self.session))
        service.process_company_action(rep, first_match.matchID, "interview")
        service.process_company_action(rep, second_match.matchID, "interview")
        service.process_company_action(rep, first_match.matchID, "offer")
        service.process_student_action(first_student, first_match.matchID, "decline")

        service.process_company_action(rep, second_match.matchID, "offer")

        self.session.expire_all()
        saved_first_match = self.session.get(Match, first_match.matchID)
        saved_second_match = self.session.get(Match, second_match.matchID)
        saved_first_application = self.session.get(
            Application,
            first_application.applicationID,
        )
        saved_position = self.session.get(Position, position.positionID)

        self.assertEqual(saved_first_match.status, "declined by student")
        self.assertEqual(saved_second_match.status, "offered")
        self.assertEqual(saved_first_application.status, "awaiting rematch")
        self.assertEqual(saved_position.status, "open")
