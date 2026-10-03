"""Database table models.

Import every table model here so ``SQLModel.metadata.create_all`` sees them.
"""

from app.models.user import User
from app.models.application import (
    Application,
    InternshipCycle,
    Skill,
    Student,
    StudentSkill,
)
from app.models.position import Company, CompanyRep, Match, Position, PositionSkill

__all__ = [
    "Application",
    "Company",
    "CompanyRep",
    "InternshipCycle",
    "Match",
    "Position",
    "PositionSkill",
    "Skill",
    "Student",
    "StudentSkill",
    "User",
]
