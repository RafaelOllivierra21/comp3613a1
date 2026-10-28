from fastapi import HTTPException, Query, status

from app.dependencies import CoordinatorDep, SessionDep
from app.repositories.matching import MatchingRepository
from app.schemas.application import ApiErrorResponse
from app.schemas.matching import (
    ApplicationListItemResponse,
    MatchCreateRequest,
    MatchCreateResponse,
    PositionSuggestionResponse,
)
from app.services.application_service import CycleClosedError
from app.services.matching_service import (
    ApplicationAlreadyPlacedError,
    ApplicationNotFoundError,
    InvalidApplicationFilterError,
    MatchingService,
    NotCoordinatorError,
    PairAlreadyMatchedError,
    PositionNotFoundError,
    PositionNotOpenError,
)

from . import api_router

API_ERROR_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ApiErrorResponse,
        "description": "Invalid filter or matching business rule.",
    },
    status.HTTP_401_UNAUTHORIZED: {
        "model": ApiErrorResponse,
        "description": "Authentication required.",
    },
    status.HTTP_403_FORBIDDEN: {
        "model": ApiErrorResponse,
        "description": "Coordinator role required.",
    },
    status.HTTP_404_NOT_FOUND: {
        "model": ApiErrorResponse,
        "description": "Application or position not found.",
    },
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ApiErrorResponse,
        "description": "Invalid request body.",
    },
}


@api_router.get(
    "/applications",
    response_model=list[ApplicationListItemResponse],
    responses=API_ERROR_RESPONSES,
)
def list_applications(
    user: CoordinatorDep,
    db: SessionDep,
    status_filter: str = Query(default="all", alias="status"),
):
    service = MatchingService(MatchingRepository(db))
    try:
        state = service.get_coordinator_dashboard_state(
            user,
            status_filter=status_filter,
        )
    except InvalidApplicationFilterError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{status_filter} not a valid status",
        ) from None

    return [
        ApplicationListItemResponse(
            applicationID=row.application.applicationID,
            studentID=row.application.studentID,
            fullName=row.student_user.fullName,
            degreeName=row.student.degreeName,
            gpa=row.student.gpa,
            status=row.application.status,
            activeMatches=row.active_match_count,
        )
        for row in state.applications
    ]


@api_router.get(
    "/applications/{application_id}/suggestions",
    response_model=list[PositionSuggestionResponse],
    responses={
        **API_ERROR_RESPONSES,
        status.HTTP_404_NOT_FOUND: {
            "model": ApiErrorResponse,
            "description": "Application not found.",
        },
    },
)
def get_application_suggestions(
    application_id: int,
    user: CoordinatorDep,
    db: SessionDep,
    show_all: bool = Query(default=False, alias="all"),
):
    service = MatchingService(MatchingRepository(db))
    try:
        state = service.get_matching_page_state(user, application_id)
    except ApplicationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"application {application_id} not found",
        ) from None

    positions = (
        state.suggested_positions + state.open_positions
        if show_all
        else state.suggested_positions
    )
    return [
        PositionSuggestionResponse(
            positionID=option.position.positionID,
            title=option.position.title,
            company=option.company.name,
            fitPercent=round(option.fit_percentage),
            matchedSkills=[skill.name for skill in option.matched_skills],
            missingSkills=[skill.name for skill in option.missing_skills],
        )
        for option in positions
    ]


@api_router.post(
    "/matches",
    response_model=MatchCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses=API_ERROR_RESPONSES,
)
def create_match(
    payload: MatchCreateRequest,
    user: CoordinatorDep,
    db: SessionDep,
):
    service = MatchingService(MatchingRepository(db))
    try:
        match = service.submit_match(
            user=user,
            application_id=payload.applicationID,
            position_id=payload.positionID,
        )
    except NotCoordinatorError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not authorized",
        ) from None
    except ApplicationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"application {payload.applicationID} not found",
        ) from None
    except PositionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"position {payload.positionID} not found",
        ) from None
    except ApplicationAlreadyPlacedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="application has already been placed",
        ) from None
    except PositionNotOpenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="position is not open for matching",
        ) from None
    except PairAlreadyMatchedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="application and position are already matched",
        ) from None
    except CycleClosedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="internship cycle is closed",
        ) from None

    return MatchCreateResponse(message="match created", matchID=match.matchID)
