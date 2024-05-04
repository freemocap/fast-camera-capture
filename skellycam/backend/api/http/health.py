from fastapi import APIRouter

from skellycam.backend.run_backend import logger

healthcheck_router = APIRouter()

@healthcheck_router.get("/hello", summary="👋")
async def hello():
    """
    A simple endpoint to greet the user of the SkellyCam API.
    This can be used as a sanity check to ensure the API is responding.
    """
    logger.api("Hello requested! Deploying Hello!")
    return {"message": "Hello from the SkellyCam Backend 💀📸✨"}
