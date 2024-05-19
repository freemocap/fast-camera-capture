import logging

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from skellycam.core.controller.singleton import get_or_create_controller

logger = logging.getLogger(__name__)

websocket_router = APIRouter()

HELLO_CLIENT_MESSAGE = "👋Hello, client!"

async def listen_for_client_messages(websocket: WebSocket):
    logger.info("Starting listener for client messages...")
    while True:
        try:
            message = await websocket.receive_text()
            logger.debug(f"Message from client: '{message}'")

            if not message:
                logger.api("Empty message received, ending listener task...")
                break
        except WebSocketDisconnect:
            logger.api("Client disconnected, ending listener task...")
            break
        except Exception as e:
            logger.error(f"Error while receiving message: {type(e).__name__} - {e}")
            break


class WebsocketRunner:
    async def __aenter__(self):
        logger.debug("WebsocketRunner started...")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.debug("WebsocketRunner ended...")
        pass


@websocket_router.websocket("/ws/connect")
async def websocket_server_connect(websocket: WebSocket):
    """
    Websocket endpoint for client connection to the server - handles image data streaming to frontend.
    """
    logger.success(f"Websocket connection established!")

    await websocket.accept()
    await websocket.send_text(HELLO_CLIENT_MESSAGE)

    async def websocket_send_bytes(data: bytes):
        logger.trace(f"Sending bytes to client: {data[:10]}...")
        await websocket.send_bytes(data)

    controller = get_or_create_controller()
    controller.set_websocket_bytes_sender(websocket_send_bytes)

    async with WebsocketRunner():
        try:
            logger.api("Creating listener task...")
            await listen_for_client_messages(websocket)

        except Exception as e:
            logger.exception(e)
            logger.error(f"Error while running camera loop: {type(e).__name__}- {e}")
        finally:
            logger.info("Closing websocket...")
            await controller.close()
            await websocket.send_text("Goodbye, client👋")
            await websocket.close()
            logger.api("Websocket closed")
