import unittest

from app.models.user import UserBase
from app.repositories.user import UserRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.utilities.security import verify_password


class UserIntegrationTests(unittest.TestCase):
    def test_register_user(self):
        repository = UserRepository(self.session)
        user = AuthService(repository).register_user(
            username="student-one",
            email="student-one@example.com",
            password="secure-password",
            full_name="Student One",
            number="868-555-0101",
        )

        self.session.expire_all()
        saved_user = repository.get_by_username("student-one")

        self.assertIsNotNone(user)
        self.assertIsNotNone(saved_user)
        self.assertEqual(saved_user.role, "student")
        self.assertNotEqual(saved_user.password, "secure-password")
        self.assertTrue(verify_password("secure-password", saved_user.password))

    def test_authenticate(self):
        repository = UserRepository(self.session)
        auth_service = AuthService(repository)
        auth_service.register_user(
            username="student-two",
            email="student-two@example.com",
            password="secure-password",
            full_name="Student Two",
            number="868-555-0102",
        )

        self.session.expire_all()
        token = auth_service.authenticate_user("student-two", "secure-password")

        self.assertIsInstance(token, str)
        self.assertTrue(token)

    def test_get_all_users(self):
        repository = UserRepository(self.session)
        repository.create(
            UserBase(
                username="user-one",
                email="user-one@example.com",
                fullName="User One",
                number="868-555-0103",
                password="stored-password-one",
                role="student",
            )
        )
        repository.create(
            UserBase(
                username="user-two",
                email="user-two@example.com",
                fullName="User Two",
                number="868-555-0104",
                password="stored-password-two",
                role="company_rep",
            )
        )

        self.session.expire_all()
        users = UserService(repository).get_all_users()

        self.assertEqual(
            {user.username for user in users},
            {"user-one", "user-two"},
        )
