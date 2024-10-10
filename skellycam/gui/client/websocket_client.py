import json
import logging
import threading
import time
from typing import Union, Dict, Any, Optional, Callable

import websocket
from websocket import WebSocketApp

from skellycam.app.app_state import AppStateDTO
from skellycam.core.frames.payloads.frontend_image_payload import FrontendFramePayload
from skellycam.core.videos.video_recorder_manager import RecordingInfo
from skellycam.gui.qt.gui_state.gui_state import GUIState, get_gui_state

logger = logging.getLogger(__name__)


class WebSocketClient:
    """
    A simple WebSocket client that connects to a WebSocket server and handles incoming messages.
    Intended to be used as part of the FastAPIClient class.
    """

    def __init__(self, base_url: str):
        self.websocket_url = base_url.replace("http", "ws") + "/websocket/connect"
        self.websocket = self._create_websocket()
        self._websocket_thread: Optional[threading.Thread] = None
        self._gui_state: GUIState = get_gui_state()
        self._image_update_callable: Optional[Callable] = None

    def _create_websocket(self):
        return websocket.WebSocketApp(
            self.websocket_url,
            on_message=self._on_message,
            on_open=self._on_open,
            on_error=self._on_error,
            on_close=self._on_close,
        )

    @property
    def connected(self) -> bool:
        return self.websocket.sock and self.websocket.sock.connected

    def connect_websocket(self) -> None:
        logger.gui(f"Connecting to WebSocket at {self.websocket_url}...")
        self._websocket_thread = threading.Thread(
            target=lambda: self.websocket.run_forever(reconnect=True, ping_interval=5),
            daemon=True)
        self._websocket_thread.start()

    def _on_open(self, ws) -> None:
        logger.gui(f"Connected to WebSocket at {self.websocket_url}, sending test messages...")

    def _on_message(self, ws: WebSocketApp, message: Union[str, bytes]) -> None:
        self._handle_websocket_message(message)

    def _on_error(self, ws: WebSocketApp, exception: Exception) -> None:
        logger.exception(f"WebSocket exception: {exception.__class__.__name__}: {exception}")
        raise

    def _on_close(self, ws: WebSocketApp, close_status_code, close_msg) -> None:
        logger.gui(f"WebSocket connection closed: Close status code: {close_status_code}, Close message: {close_msg}")

    def _handle_websocket_message(self, message: Union[str, bytes]) -> None:
        if isinstance(message, str):
            try:
                json_data = json.loads(message)
                self._handle_json_message(json_data)
            except json.JSONDecodeError:
                logger.gui(f"Received text message: {message}")
                self._handle_text_message(message)
        elif isinstance(message, bytes):
            logger.gui(f"Received binary message: size: {len(message) * .001:.3f}kB")
            self._handle_binary_message(message)

    def _handle_text_message(self, message: str) -> None:
        logger.gui(f"Received text message: {message}")
        pass

    def _handle_binary_message(self, message: bytes) -> None:

        payload = json.loads(message)

        if 'jpeg_images' in payload.keys():
            fe_payload = FrontendFramePayload(**payload)
            logger.gui(
                f"Received FrontendFramePayload with {len(fe_payload.camera_ids)} cameras - size: {len(message)} bytes")
            fe_payload.lifespan_timestamps_ns.append({"unpickled_from_websocket": time.perf_counter_ns()})
            self._gui_state.latest_frontend_payload = fe_payload
        elif 'recording_name' in payload.keys():
            logger.gui(f"Received RecordingInfo object  - {payload}")
            self._gui_state.recording_info = RecordingInfo(**payload)
        else:
            logger.gui(f"Received binary message: {len(payload) * .001:.3f}kB")

    def _handle_json_message(self, message: Dict[str, Any]) -> None:
        if isinstance(message, str):
            message = json.loads(message)
        try:
            if "message" in message.keys():
                logger.gui(f"Received message: {message['message']}")
            elif 'jpeg_images' in message.keys():
                fe_payload = FrontendFramePayload(**message)
                self._gui_state.latest_frontend_payload = fe_payload
            elif 'recording_name' in message.keys():
                recording_info = RecordingInfo(**message)
                logger.gui(f"Received RecordingInfo for recording: `{recording_info.recording_name}`")
                self._gui_state.recording_info = recording_info
            elif 'camera_configs' in message.keys():
                app_state = AppStateDTO(**message)
                logger.gui(f"Received AppStateDTO (state_timestamp: {app_state.state_timestamp})")
                self._gui_state.update_app_state(app_state_dto=app_state)
            else:
                logger.gui(f"Received JSON message, size: {len(json.dumps(message))} bytes")
        except Exception as e:
            logger.exception(e)
            raise

    def close(self) -> None:

        if self.websocket:
            try:
                self.websocket.close()
            except websocket.WebSocketConnectionClosedException:
                pass
        self.websocket = self._create_websocket()
        logger.gui("Closing WebSocket client")
        if self._websocket_thread:
            self._websocket_thread.join()
