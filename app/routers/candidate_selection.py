from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.candidate_selection import CandidateSelectionRepository
from . import router
from app.services.candidate_selection_service import (
    CandidateSelectionService,
    InvalidActionError,
    MatchIDNotFoundError,
    MatchNotInCompanyError,
    MatchNotInStudentError,
    NotAStudentError,
    NotACompanyRepError,
    OfferAlreadyPendingError,
)
from app.utilities.flash import flash
from . import templates


@router.get(
    "/rep/positions",
    response_class=HTMLResponse,
    name="company_rep_dashboard_view",
)
def company_rep_dashboard_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    service = CandidateSelectionService(CandidateSelectionRepository(db))
    try:
        state = service.get_company_rep_dashboard_state(user)
    except NotACompanyRepError:
        flash(request, "This dashboard is available to company representatives only.", "danger")
        return RedirectResponse(
            request.url_for("user_home_view"),
            status_code=303,
        )
    return templates.TemplateResponse(
        request=request,
        name="company_rep.html",
        context={"user": user, "state": state},
    )

@router.post(
    "/rep/matches/{match_id}/action",
    name="company_candidate_action",
)
def company_candidate_action(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    match_id: int,
    action: str = Form(),
):
    # STUDENT SNIPPET START: thin Company Rep candidate action handler.
    service = CandidateSelectionService(CandidateSelectionRepository(db))
    dashboard = request.url_for("company_rep_dashboard_view")
    try:
        service.process_company_action(
            user=user,
            match_id=match_id,
            action=action,
        )
    except NotACompanyRepError:
        flash(request, "You are not a company representative.", "danger")
        return RedirectResponse(request.url_for("user_home_view"), status_code=303)
    except MatchIDNotFoundError:
        flash(request, "Match not found.", "danger")
        return RedirectResponse(dashboard, status_code=303)
    except MatchNotInCompanyError:
        flash(request, "Match is not associated with your company.", "danger")
        return RedirectResponse(dashboard, status_code=303)
    except InvalidActionError:
        flash(request, "That action isn't allowed for this candidate's current status.", "danger")
        return RedirectResponse(dashboard, status_code=303)
    except OfferAlreadyPendingError:
        flash(request, "Another candidate already has an offer pending for this position.", "danger")
        return RedirectResponse(dashboard, status_code=303)
    flash(request, "Action processed successfully.")
    # STUDENT SNIPPET END

    return RedirectResponse(
        url=request.url_for("company_rep_dashboard_view"),
        status_code=303,
    )


@router.post(
    "/app/matches/{match_id}/action",
    name="student_match_action",
)
def student_match_action(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    match_id: int,
    action: str = Form(),
):
    service = CandidateSelectionService(CandidateSelectionRepository(db))
    try:
        service.process_student_action(
            user=user,
            match_id=match_id,
            action=action,
        )
    except NotAStudentError:
        flash(request, "This action is available to student accounts only.", "danger")
        return RedirectResponse(request.url_for("index_view"), status_code=303)
    except MatchIDNotFoundError:
        flash(request, "Match not found.", "danger")
    except MatchNotInStudentError:
        flash(request, "This match does not belong to your application.", "danger")
    except InvalidActionError:
        flash(request, "That action isn't available for this match.", "danger")
    else:
        flash(request, "Your response has been recorded.", "success")
    return RedirectResponse(
        url=request.url_for("user_home_view"),
        status_code=303,
    )
