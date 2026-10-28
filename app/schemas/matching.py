from pydantic import BaseModel


class ApplicationListItemResponse(BaseModel):
    applicationID: int
    studentID: int
    fullName: str
    degreeName: str
    gpa: float
    status: str
    activeMatches: int


class PositionSuggestionResponse(BaseModel):
    positionID: int
    title: str
    company: str
    fitPercent: int
    matchedSkills: list[str]
    missingSkills: list[str]


class MatchCreateRequest(BaseModel):
    applicationID: int
    positionID: int


class MatchCreateResponse(BaseModel):
    message: str
    matchID: int
