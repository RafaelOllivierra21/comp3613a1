from datetime import date
import unittest

from app.models.position import Company, CompanyRep, Position
from app.models.user import UserBase
from app.repositories.matching import MatchingRepository
from app.repositories.user import UserRepository
from app.services.position_posting_service import PositionPostingService
from app.repositories.position_posting import PositionPostingRepository


class PositionPostingIntegrationTests(unittest.TestCase):
    def _create_company_rep(self):
        company = Company(name="Example Company", location="Port of Spain")
        self.session.add(company)
        self.session.flush()
        self.assertIsNotNone(company.companyID)

        user = UserRepository(self.session).create(
            UserBase(
                username="company-rep",
                email="company-rep@example.com",
                fullName="Company Representative",
                number="868-555-0106",
                password="stored-password",
                role="company_rep",
            )
        )
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.id)
        self.session.add(CompanyRep(userID=user.id, companyID=company.companyID))
        self.session.commit()
        return user, company

    def test_create_position(self):
        user, company = self._create_company_rep()
        position = PositionPostingService(
            PositionPostingRepository(self.session)
        ).create_position(
            user=user,
            title="  IT Intern  ",
            description="  Support desk  ",
            skill_ids=[1, 2],
        )

        self.session.expire_all()
        saved_position = self.session.get(Position, position.positionID)
        required_skills = MatchingRepository(self.session).get_required_skills(
            [position.positionID]
        )

        self.assertIsNotNone(saved_position)
        self.assertEqual(saved_position.companyID, company.companyID)
        self.assertEqual(saved_position.cycleID, 1)
        self.assertEqual(saved_position.title, "IT Intern")
        self.assertEqual(saved_position.description, "Support desk")
        self.assertEqual(saved_position.status, "open")
        self.assertEqual(saved_position.dateOpened, date.today())
        self.assertEqual(
            {skill.skillID for skill in required_skills[position.positionID]},
            {1, 2},
        )
