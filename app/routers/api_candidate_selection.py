from fastapi import HTTPException, status

from app.dependencies import ApiAuthDep, CompanyRepDep, SessionDep
from app.repositories.candidate_selection import CandidateSelectionRepository
from app.schemas.application import ApiErrorResponse
from app.schemas.candidate_selection import (
    CompanyPositionResponse,
    MatchUpdateRequest,
    MatchUpdateResponse,
)
from app.services.candidate_selection_service import (
    CandidateSelectionService,
    InvalidActionError,
    MatchIDNotFoundError,
    MatchNotInCompanyError,
    MatchNotInStudentError,
    NotACompanyRepError,
    NotAStudentError,
    OfferAlreadyPendingError,
)

from . import api_router

API_ERROR_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ApiErrorResponse,
        "description": "Invalid status or candidate action business rule.",
    },
    status.HTTP_401_UNAUTHORIZED: {
        "model": ApiErrorResponse,
        "description": "Authentication required.",
    },
    status.HTTP_403_FORBIDDEN: {
        "model": ApiErrorResponse,
        "description": "Company representative or student access required.",
    },
    status.HTTP_404_NOT_FOUND: {
        "model": ApiErrorResponse,
        "description": "Match not found.",
    },
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ApiErrorResponse,
        "description": "Invalid request body.",
    },
}

COMPANY_STATUS_ACTIONS = {
    "interviewing": "interview",
    "offered": "offer",
    "rejected by company": "reject",
}
STUDENT_STATUS_ACTIONS = {
    "accepted": "accept",
    "declined by student": "decline",
}


@api_router.get(
    "/positions/mine",
    response_model=list[CompanyPositionResponse],
    responses=API_ERROR_RESPONSES,
)
def get_my_positions(user: CompanyRepDep, db: SessionDep):
    service = CandidateSelectionService(CandidateSelectionRepository(db))
    try:
        state = service.get_company_rep_dashboard_state(user)
    except NotACompanyRepError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not authorized",
        ) from None

    return [
        CompanyPositionResponse(
            positionID=card.position.positionID,
            title=card.position.title,
            status=card.position.status,
            dateOpened=card.position.dateOpened,
            candidates=[
                {
                    "matchID": candidate.match.matchID,
                    "fullName": candidate.student_user.fullName,
                    "degreeName": candidate.student.degreeName,
                    "gpa": candidate.student.gpa,
                    "email": candidate.student_user.email,
                    "number": candidate.student_user.number,
                    "resumeLink": candidate.student.resumeLink,
                    "status": candidate.match.status,
                }
                for candidate in card.candidates
            ],
        )
        for card in state.positions
    ]


@api_router.put(
    "/matches/{match_id}",
    response_model=MatchUpdateResponse,
    status_code=status.HTTP_201_CREATED,
    responses=API_ERROR_RESPONSES,
)
def update_match(
    match_id: int,
    payload: MatchUpdateRequest,
    user: ApiAuthDep,
    db: SessionDep,
):
    role = user.role.strip().casefold()
    if role == "company_rep":
        action = COMPANY_STATUS_ACTIONS.get(payload.status)
        if action is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.status} not a valid status",
            )
        service = CandidateSelectionService(CandidateSelectionRepository(db))
        try:
            service.process_company_action(user, match_id, action)
        except NotACompanyRepError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="not authorized",
            ) from None
        except MatchIDNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"match {match_id} not found",
            ) from None
        except MatchNotInCompanyError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="not authorized",
            ) from None
        except OfferAlreadyPendingError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="another offer is already pending for this position",
            ) from None
        except InvalidActionError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="action is not allowed for this match",
            ) from None
    elif role == "student":
        action = STUDENT_STATUS_ACTIONS.get(payload.status)
        if action is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.status} not a valid status",
            )
        service = CandidateSelectionService(CandidateSelectionRepository(db))
        try:
            service.process_student_action(user, match_id, action)
        except NotAStudentError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="not authorized",
            ) from None
        except MatchIDNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"match {match_id} not found",
            ) from None
        except MatchNotInStudentError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="not authorized",
            ) from None
        except InvalidActionError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="match has no pending offer",
            ) from None
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not authorized",
        )

    return MatchUpdateResponse(message="match updated", status=payload.status)
