from fastapi import HTTPException, status

from app.dependencies import CoordinatorDep, SessionDep
from app.repositories.cycle_closure import CycleClosureRepository
from app.schemas.application import ApiErrorResponse
from app.schemas.cycle_closure import CycleClosureRequest, CycleClosureResponse
from app.services.application_service import CycleClosedError
from app.services.cycle_closure_service import CycleClosureService

from . import api_router

API_ERROR_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ApiErrorResponse,
        "description": "Invalid status or already closed internship cycle.",
    },
    status.HTTP_401_UNAUTHORIZED: {
        "model": ApiErrorResponse,
        "description": "Authentication required.",
    },
    status.HTTP_403_FORBIDDEN: {
        "model": ApiErrorResponse,
        "description": "Coordinator access required.",
    },
    status.HTTP_404_NOT_FOUND: {
        "model": ApiErrorResponse,
        "description": "Internship cycle not found.",
    },
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ApiErrorResponse,
        "description": "Invalid request body.",
    },
}


@api_router.put(
    "/cycles/{cycle_id}",
    response_model=CycleClosureResponse,
    status_code=status.HTTP_201_CREATED,
    responses=API_ERROR_RESPONSES,
)
def close_cycle(
    cycle_id: int,
    payload: CycleClosureRequest,
    user: CoordinatorDep,
    db: SessionDep,
):
    if payload.status != "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{payload.status} not a valid status",
        )

    repository = CycleClosureRepository(db)
    cycle = repository.get_current_cycle()
    if cycle is None or cycle.cycleID != cycle_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"cycle {cycle_id} not found",
        )

    service = CycleClosureService(repository)
    try:
        applications_not_matched = service.close_cycle(user)
    except CycleClosedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cycle is already closed",
        ) from None

    return CycleClosureResponse(
        message="cycle closed",
        applicationsNotMatched=applications_not_matched,
    )
