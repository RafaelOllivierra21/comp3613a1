from datetime import date
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Company(SQLModel, table=True):
    companyID: Optional[int] = Field(default=None, primary_key=True)
    name: str
    location: str


class CompanyRep(SQLModel, table=True):
    repID: Optional[int] = Field(default=None, primary_key=True)
    userID: int = Field(foreign_key="user.id", unique=True)
    companyID: int = Field(foreign_key="company.companyID", unique=True)


class Position(SQLModel, table=True):
    positionID: Optional[int] = Field(default=None, primary_key=True)
    companyID: int = Field(foreign_key="company.companyID")
    cycleID: int = Field(foreign_key="internshipcycle.cycleID")
    title: str
    description: str
    dateOpened: date
    status: str


class Match(SQLModel, table=True):
    matchID: Optional[int] = Field(default=None, primary_key=True)
    applicationID: int = Field(foreign_key="application.applicationID")
    positionID: int = Field(foreign_key="position.positionID")
    matchDate: date
    status: str

    # STUDENT SNIPPET START: prevent duplicate application/position matches.
    __table_args__ = (
        UniqueConstraint("applicationID", "positionID", name="uq_match_application_position"),
    )
    # STUDENT SNIPPET END


class PositionSkill(SQLModel, table=True):
    positionID: int = Field(foreign_key="position.positionID", primary_key=True)
    skillID: int = Field(foreign_key="skill.skillID", primary_key=True)
