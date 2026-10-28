from pydantic import BaseModel


class PositionPostingRequest(BaseModel):
    title: str
    description: str
    skillIDs: list[int]


class PositionPostingResponse(BaseModel):
    message: str
    positionID: int
