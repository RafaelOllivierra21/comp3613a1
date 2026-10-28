from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

from app.config import get_settings
from app.utilities.flash import get_flashed_messages
from app.utilities.status import status_badge_class, status_label

template_env = Environment(loader=FileSystemLoader("app/templates"))
template_env.globals['get_flashed_messages'] = get_flashed_messages
template_env.filters["status_badge_class"] = status_badge_class
template_env.filters["status_label"] = status_label
templates = Jinja2Templates(env=template_env)
static_files = StaticFiles(directory="app/static")

router = APIRouter(tags=["Jinja Based Endpoints"], include_in_schema=get_settings().env.lower() in ["dev","development"])
api_router = APIRouter(tags=["API Endpoints"], prefix="/api")

from . import (
    admin_home,
    application,
    candidate_selection,
    index,
    login,
    logout,
    matching,
    position_posting,
    register,
    server_config,
    user_home,
    users,
)
from . import (
    api_applications as api_applications,
)
from . import (
    api_auth as api_auth,
)
from . import (
    api_matching as api_matching,
)
from . import (
    api_candidate_selection as api_candidate_selection,
)
from . import (
    api_cycle_closure as api_cycle_closure,
)
from . import (
    api_position_posting as api_position_posting,
)
