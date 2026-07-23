"""FastAPI application factory (`just dev` serves this via --factory)."""

import logging

from fastapi import FastAPI

from flowstate import __version__
from flowstate.app import chat, health
from flowstate.config import get_settings
from flowstate.core.agent import SdkAgentBackend
from flowstate.core.workspace import Workspace
from flowstate.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    app = FastAPI(title="FlowState runtime", version=__version__)
    workspace = Workspace(settings.workspace_dir).ensure()
    app.state.agent_backend = SdkAgentBackend(settings, workspace)
    app.include_router(health.router)
    app.include_router(chat.router)
    logger.info("runtime configured", extra={"environment": settings.environment})
    return app
