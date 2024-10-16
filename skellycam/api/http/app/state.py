import logging

from fastapi import APIRouter

from skellycam.app.app_controller.app_controller import get_app_controller

logger = logging.getLogger(__name__)
state_router = APIRouter()


@state_router.get("/state", summary="Application State")
async def app_state_endpoint():
    """
    A simple endpoint that serves the current state of the application
    """
    logger.api("Serving application state from `app/state` endpoint...")

    return get_app_controller().app_state.state_dto()
