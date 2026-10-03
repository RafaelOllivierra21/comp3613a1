from datetime import date
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class InternshipCycle(SQLModel, table=True):
    cycleID: Optional[int] = Field(default=None, primary_key=True)
    startDate: date
    endDate: date
    status: str


class Student(SQLModel, table=True):
    studentID: int = Field(primary_key=True)
    userID: int = Field(foreign_key="user.id", unique=True)
    gpa: float
    degreeName: str
    expectedGraduationDate: date
    resumeLink: str


class Application(SQLModel, table=True):
    applicationID: Optional[int] = Field(default=None, primary_key=True)
    studentID: int = Field(foreign_key="student.studentID")
    cycleID: int = Field(foreign_key="internshipcycle.cycleID")
    dateSubmitted: date
    status: str = "submitted"

    # STUDENT SNIPPET START: named student/cycle unique constraint.
    __table_args__ = (
        UniqueConstraint("studentID", "cycleID", name="uq_application_student_cycle"),
    )
    # STUDENT SNIPPET END


class Skill(SQLModel, table=True):
    skillID: Optional[int] = Field(default=None, primary_key=True)
    name: str


class StudentSkill(SQLModel, table=True):
    studentID: int = Field(foreign_key="student.studentID", primary_key=True)
    skillID: int = Field(foreign_key="skill.skillID", primary_key=True)
