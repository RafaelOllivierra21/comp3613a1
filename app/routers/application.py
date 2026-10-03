from datetime import date

from fastapi import Form, Request
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.application import ApplicationRepository
from app.services.application_service import (ApplicationService, AlreadyAppliedError, CycleClosedError,
                                               StudentIDTakenError, InvalidStudentIDInputError, InvalidGPAInputError, InvalidDegreeNameInputError, 
                                               InvalidExpectedGraduationDateInputError, InvalidResumeLinkInputError,
                                               InvalidSkillIDsInputError, NotAStudentError)   
from app.utilities.flash import flash
from . import router, templates


@router.get("/app/application", response_class=HTMLResponse, name="application_view")
def application_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    service = ApplicationService(ApplicationRepository(db))
    try:
        state = service.get_application_page_state(user)
    except NotAStudentError:
        flash(request, "This application is available to student accounts only.", "danger")
        return RedirectResponse(
            url=request.url_for("index_view"),
            status_code=303,
        )
    except CycleClosedError:
        flash(request, "Applications are closed for this cycle.", "danger")
        return RedirectResponse(
            url=request.url_for("user_home_view"),
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="application.html",
        context={
            "user": user,
            "state": state,
            "read_only": state.application is not None,
            "application_submitted": state.application is not None,
        },
    )


@router.post("/app/application", name="submit_application")
def submit_application(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    studentID: int = Form(),
    gpa: float = Form(),
    degreeName: str = Form(),
    expectedGraduationDate: date = Form(),
    resumeLink: str = Form(),
    skillIDs: list[int] = Form(default=[]),
):
    # STUDENT SNIPPET START: thin handler using the service.
    service = ApplicationService(ApplicationRepository(db))
    try:
        service.submit_application(
            user=user,
            student_id=studentID,
            gpa=gpa,
            degree_name=degreeName,
            expected_graduation_date=expectedGraduationDate,
            resume_link=resumeLink,
            skill_ids=skillIDs,
        )
    except NotAStudentError:
        flash(request, "You must be a student to submit an application.", "danger")
        return RedirectResponse(request.url_for("index_view"), status_code=303)
    except AlreadyAppliedError:
        flash(request, "You have already applied for this cycle.", "danger")
        return RedirectResponse(request.url_for("application_view"), status_code=303)
    except CycleClosedError:
        flash(request, "The application cycle is closed.", "danger")
        return RedirectResponse(request.url_for("user_home_view"), status_code=303)
    except StudentIDTakenError:
        flash(request, "The provided student ID is already in use.", "danger")
        return RedirectResponse(request.url_for("application_view"), status_code=303)
    except InvalidStudentIDInputError:
        flash(request, "Please enter a valid UWI Student ID.", "danger")
        return RedirectResponse(request.url_for("application_view"), status_code=303)
    except InvalidGPAInputError:
        flash(request, "Please enter a GPA between 0 and 4.3.", "danger")
        return RedirectResponse(request.url_for("application_view"), status_code=303)
    except InvalidDegreeNameInputError:
        flash(request, "Please enter a degree name.", "danger")
        return RedirectResponse(request.url_for("application_view"), status_code=303)
    except InvalidExpectedGraduationDateInputError:
        flash(request, "Please enter a valid expected graduation date.", "danger")
        return RedirectResponse(request.url_for("application_view"), status_code=303)
    except InvalidResumeLinkInputError:
        flash(request, "Please enter a valid resume URL.", "danger")
        return RedirectResponse(request.url_for("application_view"), status_code=303)
    except InvalidSkillIDsInputError:
        flash(request, "Please select at least one valid skill.", "danger")
        return RedirectResponse(request.url_for("application_view"), status_code=303)
    flash(request, "Application submitted successfully!", "success")
    return RedirectResponse(request.url_for("user_home_view"), status_code=303)
    # STUDENT SNIPPET END
