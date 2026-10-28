from datetime import date

from pydantic import BaseModel, EmailStr


class CompanyCandidateResponse(BaseModel):
    matchID: int
    fullName: str
    degreeName: str
    gpa: float
    email: EmailStr
    number: str
    resumeLink: str
    status: str


class CompanyPositionResponse(BaseModel):
    positionID: int
    title: str
    status: str
    dateOpened: date
    candidates: list[CompanyCandidateResponse]


class MatchUpdateRequest(BaseModel):
    status: str


class MatchUpdateResponse(BaseModel):
    message: str
    status: str
