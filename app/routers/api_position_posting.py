from fastapi import HTTPException, status

from app.dependencies import CompanyRepDep, SessionDep
from app.repositories.position_posting import PositionPostingRepository
from app.schemas.application import ApiErrorResponse
from app.schemas.position_posting import (
    PositionPostingRequest,
    PositionPostingResponse,
)
from app.services.application_service import CycleClosedError
from app.services.candidate_selection_service import NotACompanyRepError
from app.services.position_posting_service import (
    InvalidDescriptionInputError,
    InvalidSkillInputError,
    InvalidTitleInputError,
    PositionPostingService,
)

from . import api_router

API_ERROR_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ApiErrorResponse,
        "description": "Invalid position input or closed internship cycle.",
    },
    status.HTTP_401_UNAUTHORIZED: {
        "model": ApiErrorResponse,
        "description": "Authentication required.",
    },
    status.HTTP_403_FORBIDDEN: {
        "model": ApiErrorResponse,
        "description": "Company representative access required.",
    },
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ApiErrorResponse,
        "description": "Invalid request body.",
    },
}


@api_router.post(
    "/positions",
    response_model=PositionPostingResponse,
    status_code=status.HTTP_201_CREATED,
    responses=API_ERROR_RESPONSES,
)
def create_position(
    payload: PositionPostingRequest,
    user: CompanyRepDep,
    db: SessionDep,
):
    service = PositionPostingService(PositionPostingRepository(db))
    try:
        position = service.create_position(
            user=user,
            title=payload.title,
            description=payload.description,
            skill_ids=payload.skillIDs,
        )
    except NotACompanyRepError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not authorized",
        ) from None
    except InvalidTitleInputError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title is invalid",
        ) from None
    except InvalidDescriptionInputError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="description is invalid",
        ) from None
    except InvalidSkillInputError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skillIDs is invalid",
        ) from None
    except CycleClosedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="internship cycle is closed",
        ) from None

    return PositionPostingResponse(
        message="position created",
        positionID=position.positionID,
    )
