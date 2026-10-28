from fastapi import HTTPException, status

from app.dependencies import SessionDep, StudentDep
from app.repositories.application import ApplicationRepository
from app.repositories.candidate_selection import CandidateSelectionRepository
from app.schemas.application import (
    ApiErrorResponse,
    ApplicationMeResponse,
    ApplicationStudentResponse,
    ApplicationSubmitRequest,
    ApplicationSubmitResponse,
    MatchResponse,
    SkillResponse,
)
from app.services.application_service import (
    AlreadyAppliedError,
    ApplicationService,
    CycleClosedError,
    InvalidDegreeNameInputError,
    InvalidExpectedGraduationDateInputError,
    InvalidGPAInputError,
    InvalidResumeLinkInputError,
    InvalidSkillIDsInputError,
    InvalidStudentIDInputError,
    NotAStudentError,
    StudentIDTakenError,
)
from app.services.candidate_selection_service import CandidateSelectionService

from . import api_router

API_ERROR_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ApiErrorResponse,
        "description": "Invalid application input or business rule.",
    },
    status.HTTP_401_UNAUTHORIZED: {
        "model": ApiErrorResponse,
        "description": "Authentication required.",
    },
    status.HTTP_403_FORBIDDEN: {
        "model": ApiErrorResponse,
        "description": "Student role required.",
    },
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ApiErrorResponse,
        "description": "Invalid request body.",
    },
}


@api_router.post(
    "/applications",
    response_model=ApplicationSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    responses=API_ERROR_RESPONSES,
)
def submit_application_api(
    payload: ApplicationSubmitRequest,
    user: StudentDep,
    db: SessionDep,
):
    service = ApplicationService(ApplicationRepository(db))
    try:
        application = service.submit_application(
            user=user,
            student_id=payload.studentID,
            gpa=payload.gpa,
            degree_name=payload.degreeName,
            expected_graduation_date=payload.expectedGraduationDate,
            resume_link=payload.resumeLink,
            skill_ids=payload.skillIDs,
        )
    except NotAStudentError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not authorized",
        ) from None
    except AlreadyAppliedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="you have already applied for this cycle",
        ) from None
    except CycleClosedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="applications are closed for this cycle",
        ) from None
    except StudentIDTakenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"student ID {payload.studentID} already taken",
        ) from None
    except InvalidStudentIDInputError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="studentID is invalid",
        ) from None
    except InvalidGPAInputError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="gpa is invalid",
        ) from None
    except InvalidDegreeNameInputError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="degreeName is invalid",
        ) from None
    except InvalidExpectedGraduationDateInputError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expectedGraduationDate is invalid",
        ) from None
    except InvalidResumeLinkInputError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resumeLink is invalid",
        ) from None
    except InvalidSkillIDsInputError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skillIDs is invalid",
        ) from None

    return {
        "message": "application submitted",
        "applicationID": application.applicationID,
    }


@api_router.get(
    "/applications/me",
    response_model=ApplicationMeResponse,
    responses={
        **API_ERROR_RESPONSES,
        status.HTTP_404_NOT_FOUND: {
            "model": ApiErrorResponse,
            "description": "No application found.",
        },
    },
)
def get_my_application(user: StudentDep, db: SessionDep):
    state = ApplicationService(ApplicationRepository(db)).get_dashboard_state(user)
    if state.application is None or state.student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no application found",
        )

    matches = CandidateSelectionService(
        CandidateSelectionRepository(db)
    ).get_student_matches(user)

    return ApplicationMeResponse(
        applicationID=state.application.applicationID,
        studentID=state.application.studentID,
        status=state.application.status,
        dateSubmitted=state.application.dateSubmitted,
        student=ApplicationStudentResponse(
            fullName=user.fullName,
            email=user.email,
            number=user.number,
            degreeName=state.student.degreeName,
            gpa=state.student.gpa,
            expectedGraduationDate=state.student.expectedGraduationDate,
            resumeLink=state.student.resumeLink,
        ),
        skills=[
            SkillResponse(skillID=skill.skillID, name=skill.name)
            for skill in state.selected_skills
        ],
        matches=[
            MatchResponse(
                matchID=card.match.matchID,
                positionID=card.position.positionID,
                title=card.position.title,
                company=card.company.name,
                status=card.match.status,
                matchDate=card.match.matchDate,
            )
            for card in matches
        ],
    )
