from datetime import date
import unittest

from app.models.position import Position
from app.models.user import User


class ModelUnitTests(unittest.TestCase):
    def test_new_user(self):
        user = User(
            username="bob",
            email="bob@mail.com",
            fullName="Bob Smith",
            number="868-555-0101",
            password="hashed-password",
            role="student",
        )

        assert user.username == "bob"
        assert user.role == "student"


    def test_new_position(self):
        position = Position(
            companyID=1,
            cycleID=1,
            title="IT Intern",
            description="Support desk",
            dateOpened=date.today(),
            status="open",
        )

        assert position.title == "IT Intern"
        assert position.status == "open"
