from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.application import ApplicationRepository
from app.services.application_service import ApplicationService, NotAStudentError
from app.utilities.flash import flash
from . import router, templates


@router.get("/app", response_class=HTMLResponse)
async def user_home_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    service = ApplicationService(ApplicationRepository(db))
    try:
        state = service.get_dashboard_state(user)
    except NotAStudentError:
        flash(request, "This dashboard is available to student accounts only.", "danger")
        return RedirectResponse(
            url=request.url_for("index_view"),
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="app.html",
        context={
            "user": user,
            "state": state,
            "application_submitted": state.application is not None,
        },
    )