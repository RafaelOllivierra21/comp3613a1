from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.repositories.matching import MatchingRepository
from app.services.application_service import CycleClosedError
from app.services.matching_service import (
    ApplicationAlreadyPlacedError,
    ApplicationNotFoundError,
    MatchingService,
    NotCoordinatorError,
    PairAlreadyMatchedError,
    PositionNotFoundError,
    PositionNotOpenError,
)
from app.utilities.flash import flash
from . import router, templates


@router.get(
    "/admin/applications/{application_id}",
    response_class=HTMLResponse,
    name="matching_view",
)
def matching_view(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    application_id: int,
):
    service = MatchingService(MatchingRepository(db))
    try:
        state = service.get_matching_page_state(user, application_id)
    except NotCoordinatorError:
        flash(request, "This screen is available to coordinator accounts only.", "danger")
        destination = (
            "admin_home_view" if user.role.casefold() == "admin" else "user_home_view"
        )
        return RedirectResponse(request.url_for(destination), status_code=303)
    except ApplicationNotFoundError:
        flash(request, "The application could not be found.", "danger")
        return RedirectResponse(request.url_for("admin_home_view"), status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="matching.html",
        context={
            "user": user,
            "state": state,
        },
    )


@router.post(
    "/admin/applications/{application_id}/positions/{position_id}/match",
    name="create_position_match",
)
def create_position_match(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    application_id: int,
    position_id: int,
):
    # STUDENT SNIPPET START: thin handler for creating a coordinator match.
    service = MatchingService(MatchingRepository(db))
    matching_screen = request.url_for("matching_view", application_id=application_id)
    try:
        service.submit_match(
            user=user,
            application_id=application_id,
            position_id=position_id,
        )
    except NotCoordinatorError:
        flash(request, "You must be a coordinator to create a match.", "danger")
        return RedirectResponse(request.url_for("user_home_view"), status_code=303)
    except ApplicationAlreadyPlacedError:
        flash(request, "The application has already been placed.", "danger")
        return RedirectResponse(matching_screen, status_code=303)
    except PositionNotOpenError:
        flash(request, "The position is not open for matching.", "danger")
        return RedirectResponse(matching_screen, status_code=303)
    except PairAlreadyMatchedError:
        flash(request, "The application and position are already matched.", "danger")
        return RedirectResponse(matching_screen, status_code=303)
    except (ApplicationNotFoundError, PositionNotFoundError):
        flash(request, "Application or position not found.", "danger")
        return RedirectResponse(request.url_for("admin_home_view"), status_code=303)
    except CycleClosedError:
        flash(request, "The internship cycle is closed.", "danger")
        return RedirectResponse(matching_screen, status_code=303)
    flash(request, "Match created successfully.", "success")
    return RedirectResponse(matching_screen, status_code=303)
    # STUDENT SNIPPET END
