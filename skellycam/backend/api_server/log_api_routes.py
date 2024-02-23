import logging

from fastapi.routing import APIRoute

logger = logging.getLogger(__name__)


def log_api_routes(app, hostname, port):
    debug_string = f"Starting Uvicorn server on `{hostname}:{port}` serving routes:\n"
    api_routes = ""
    for route in app.routes:
        if isinstance(route, APIRoute):
            api_routes += f"\tRoute: `{route.name}`, path: `{route.path}`, methods: {route.methods}\n"
    logger.info(debug_string)
