from fastapi import HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.matching import MatchingRepository
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
):
    if user.role.casefold() == "admin":
        return templates.TemplateResponse(
            request=request,
            name="admin.html",
            context={"user": user},
        )

    service = MatchingService(MatchingRepository(db))
    try:
        state = service.get_coordinator_dashboard_state(user, status_filter)
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
