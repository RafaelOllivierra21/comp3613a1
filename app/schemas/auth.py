from pydantic import EmailStr
from sqlmodel import SQLModel


class SigninRequest(SQLModel):
    username: str
    password: str

class SignupRequest(SQLModel):
    username: str
    email: str
    password: str


class ApiSignupRequest(SQLModel):
    username: str
    password: str
    fullName: str
    email: EmailStr
    number: str


class ApiSigninRequest(SQLModel):
    username: str
    password: str