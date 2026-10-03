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

__all__ = [
    "Application",
    "InternshipCycle",
    "Skill",
    "Student",
    "StudentSkill",
    "User",
]
