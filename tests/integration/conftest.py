from datetime import date

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.models import InternshipCycle, Skill


@pytest.fixture(autouse=True)
def isolated_database(request):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            InternshipCycle(
                startDate=date.today(),
                endDate=date.today(),
                status="open",
            )
        )
        session.add_all(
            [
                Skill(skillID=1, name="Python"),
                Skill(skillID=2, name="SQL"),
                Skill(skillID=3, name="Communication"),
            ]
        )
        session.commit()
        request.instance.session = session
        yield

    SQLModel.metadata.drop_all(engine)
    engine.dispose()
