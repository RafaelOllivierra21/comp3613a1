from pydantic import BaseModel


class CycleClosureRequest(BaseModel):
    status: str


class CycleClosureResponse(BaseModel):
    message: str
    applicationsNotMatched: int
