from datetime import date, timedelta
import unittest

import pytest
from sqlmodel import select

from app.models.application import Application
from app.models.position import Company, CompanyRep, Match
from app.models.user import UserBase
from app.repositories.application import ApplicationRepository
from app.repositories.matching import MatchingRepository
from app.repositories.position_posting import PositionPostingRepository
from app.repositories.user import UserRepository
from app.services.application_service import ApplicationService
from app.services.auth_service import AuthService
from app.services.matching_service import MatchingService, PairAlreadyMatchedError
from app.services.position_posting_service import PositionPostingService


class MatchingIntegrationTests(unittest.TestCase):
    def _create_student_application(self):
        user = AuthService(UserRepository(self.session)).register_user(
            username="matching-student",
            email="matching-student@example.com",
            password="secure-password",
            full_name="Matching Student",
            number="868-555-0107",
        )
        application = ApplicationService(
            ApplicationRepository(self.session)
        ).submit_application(
            user=user,
            student_id=2001,
            gpa=3.5,
            degree_name="Computer Science",
            expected_graduation_date=date.today() + timedelta(days=365),
            resume_link="https://example.com/resume",
            skill_ids=[1, 2],
        )
        return application

    def _create_position_and_coordinator(self):
        company = Company(name="Matching Company", location="San Fernando")
        self.session.add(company)
        self.session.flush()
        rep = UserRepository(self.session).create(
            UserBase(
                username="matching-rep",
                email="matching-rep@example.com",
                fullName="Matching Representative",
                number="868-555-0108",
                password="stored-password",
                role="company_rep",
            )
        )
        coordinator = UserRepository(self.session).create(
            UserBase(
                username="matching-coordinator",
                email="matching-coordinator@example.com",
                fullName="Matching Coordinator",
                number="868-555-0109",
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
        position = PositionPostingService(
            PositionPostingRepository(self.session)
        ).create_position(
            user=rep,
            title="Matching Intern",
            description="Support the team",
            skill_ids=[1, 2],
        )
        return position, coordinator

    def test_submit_match(self):
        application = self._create_student_application()
        position, coordinator = self._create_position_and_coordinator()

        match = MatchingService(MatchingRepository(self.session)).submit_match(
            user=coordinator,
            application_id=application.applicationID,
            position_id=position.positionID,
        )

        self.session.expire_all()
        current_matches = MatchingRepository(self.session).get_current_matches(
            application.applicationID
        )
        saved_application = self.session.get(Application, application.applicationID)

        self.assertEqual(len(current_matches), 1)
        saved_match = current_matches[0][0]
        self.assertEqual(saved_match.applicationID, application.applicationID)
        self.assertEqual(saved_match.positionID, position.positionID)
        self.assertEqual(saved_match.status, "matched")
        self.assertEqual(saved_application.status, "matched")

    def test_match_pair_twice(self):
        application = self._create_student_application()
        position, coordinator = self._create_position_and_coordinator()
        service = MatchingService(MatchingRepository(self.session))
        service.submit_match(
            user=coordinator,
            application_id=application.applicationID,
            position_id=position.positionID,
        )

        with pytest.raises(PairAlreadyMatchedError):
            service.submit_match(
                user=coordinator,
                application_id=application.applicationID,
                position_id=position.positionID,
            )

        self.session.expire_all()
        matches = self.session.exec(
            select(Match).where(
                Match.applicationID == application.applicationID,
                Match.positionID == position.positionID,
            )
        ).all()

        self.assertEqual(len(matches), 1)
