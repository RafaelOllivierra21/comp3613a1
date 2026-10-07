from fastapi import HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.cycle_closure import CycleClosureRepository
from app.repositories.matching import MatchingRepository
from app.services.application_service import CycleClosedError
from app.services.cycle_closure_service import CycleClosureService
from app.services.matching_service import (
    InvalidApplicationFilterError,
    MatchingService,
    NotCoordinatorError,
)
from app.utilities.flash import flash
from . import router, templates


@router.get("/admin", response_class=HTMLResponse)
def admin_home_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    status_filter: str = Query(default="all", alias="status"),
    search_query: str = Query(default="", alias="q"),
):
    service = MatchingService(MatchingRepository(db))
    try:
        state = service.get_coordinator_dashboard_state(
            user,
            status_filter,
            search_query,
        )
    except NotCoordinatorError:
        flash(request, "This dashboard is available to coordinator accounts only.", "danger")
        return RedirectResponse(
            request.url_for("user_home_view"),
            status_code=303,
        )
    except InvalidApplicationFilterError as exc:
        raise HTTPException(
            status_code=400,
            detail="Unknown application status filter.",
        ) from exc

    return templates.TemplateResponse(
        request=request,
        name="coordinator.html",
        context={
            "user": user,
            "state": state,
        },
    )


@router.post("/admin/cycle/close", name="close_internship_cycle")
def close_internship_cycle(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    # STUDENT SNIPPET START: thin handler to close the current internship cycle.
    service = CycleClosureService(CycleClosureRepository(db))
    dashboard = request.url_for("admin_home_view")
    try:
        not_matched_count = service.close_cycle(user=user)
    except NotCoordinatorError:
        flash(request, "You must be a coordinator to close the internship cycle.", "danger")
        return RedirectResponse(request.url_for("user_home_view"), status_code=303)
    except CycleClosedError:
        flash(request, "The internship cycle is already closed.", "danger")
        return RedirectResponse(dashboard, status_code=303)
    flash(request, f"Internship cycle closed successfully. {not_matched_count} application(s) were marked as not matched.", "success")
    return RedirectResponse(dashboard, status_code=303)
    # STUDENT SNIPPET END
