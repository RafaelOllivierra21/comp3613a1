from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.position_posting import PositionPostingRepository
from app.services.position_posting_service import (
    InvalidDescriptionInputError,
    InvalidSkillInputError,
    InvalidTitleInputError,
    PositionPostingService,
)
from app.services.candidate_selection_service import NotACompanyRepError
from app.services.application_service import CycleClosedError
from app.utilities.flash import flash
from . import router, templates


@router.get(
    "/rep/positions/new",
    response_class=HTMLResponse,
    name="post_position_view",
)
def post_position_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    service = PositionPostingService(PositionPostingRepository(db))
    try:
        state = service.get_form_state(user)
    except NotACompanyRepError:
        flash(request, "This page is available to company representatives only.", "danger")
        return RedirectResponse(request.url_for("user_home_view"), status_code=303)
    except CycleClosedError:
        flash(request, "The internship cycle is closed. New positions cannot be posted.", "danger")
        return RedirectResponse(request.url_for("company_rep_dashboard_view"), status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="post_position.html",
        context={"user": user, "state": state},
    )


@router.post("/rep/positions", name="post_position")
def post_position(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    title: str = Form(),
    description: str = Form(),
    skillIDs: list[int] = Form(default=[]),
):
    # STUDENT SNIPPET START: thin handler for posting an open position.
    service = PositionPostingService(PositionPostingRepository(db))
    dashboard = request.url_for("company_rep_dashboard_view")
    form_page = request.url_for("post_position_view")
    try:
        service.create_position(
            user=user,
            title=title,
            description=description,
            skill_ids=skillIDs,
        )
    except NotACompanyRepError:
        flash(request, "You must be a company representative to post positions.", "danger")
        return RedirectResponse(request.url_for("user_home_view"), status_code=303)
    except CycleClosedError:
        flash(request, "The internship cycle is closed. You cannot post new positions.", "danger")
        return RedirectResponse(dashboard, status_code=303)
    except InvalidTitleInputError:
        flash(request, "Please enter a valid position title.", "danger")
        return RedirectResponse(form_page, status_code=303)
    except InvalidDescriptionInputError:
        flash(request, "Please enter a valid position description.", "danger")
        return RedirectResponse(form_page, status_code=303)
    except InvalidSkillInputError:
        flash(request, "Please select at least one valid skill.", "danger")
        return RedirectResponse(form_page, status_code=303)
    flash(request, "Position posted successfully.", "success")
    return RedirectResponse(dashboard, status_code=303)
    # STUDENT SNIPPET END
