import jwt
import unittest

from app.config import get_settings
from app.utilities.security import (
    create_access_token,
    encrypt_password,
    verify_password,
)


class SecurityUnitTests(unittest.TestCase):
    def test_hashed_password(self):
        assert encrypt_password("mypass") != "mypass"


    def test_check_password(self):
        assert verify_password("mypass", encrypt_password("mypass")) is True


    def test_check_wrong_password(self):
        assert verify_password("wrong", encrypt_password("mypass")) is False


    def test_create_token(self):
        token = create_access_token({"sub": "1", "role": "student"})
        settings = get_settings()
        decoded = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        assert decoded["sub"] == "1"
        assert decoded["role"] == "student"
        assert "exp" in decoded
