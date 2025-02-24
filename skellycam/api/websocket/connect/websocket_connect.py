import logging

from fastapi import APIRouter, WebSocket

from skellycam.api.websocket.connect.websocket_server import WebsocketServer

logger = logging.getLogger(__name__)

websocket_router = APIRouter()


@websocket_router.websocket("/connect")
async def websocket_server_connect(websocket: WebSocket):
    await websocket.accept()
    logger.success(f"Websocket connection established!")
    async with WebsocketServer(websocket=websocket) as websocket_server:
        await websocket_server.run()
    logger.info("Websocket closed")

