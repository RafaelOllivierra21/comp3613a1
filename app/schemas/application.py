from datetime import date

from pydantic import BaseModel, EmailStr


class ApiErrorResponse(BaseModel):
    error: str


class ApplicationSubmitRequest(BaseModel):
    studentID: int
    gpa: float
    degreeName: str
    expectedGraduationDate: date
    resumeLink: str
    skillIDs: list[int]


class ApplicationSubmitResponse(BaseModel):
    message: str
    applicationID: int


class ApplicationStudentResponse(BaseModel):
    fullName: str
    email: EmailStr
    number: str
    degreeName: str
    gpa: float
    expectedGraduationDate: date
    resumeLink: str


class SkillResponse(BaseModel):
    skillID: int
    name: str


class MatchResponse(BaseModel):
    matchID: int
    positionID: int
    title: str
    company: str
    status: str
    matchDate: date


class ApplicationMeResponse(BaseModel):
    applicationID: int
    studentID: int
    status: str
    dateSubmitted: date
    student: ApplicationStudentResponse
    skills: list[SkillResponse]
    matches: list[MatchResponse]
