from PySide6.QtCore import Signal, QObject, QThread

from skellycam.api.frontend_client.api_client import FrontendApiClient
from skellycam.backend.models.cameras.frames.frame_payload import MultiFramePayload
from skellycam.backend.system.environment.get_logger import logger


class FrameGrabber(QThread):
    new_frames = Signal(MultiFramePayload)

    def __init__(self, api_client: FrontendApiClient, parent: QObject):
        super().__init__(parent=parent)
        self.api_client = api_client
        self.should_continue = True

    def run(self):
        logger.info(f"FrameGrabber starting...")

        while self.should_continue:
            try:
                logger.trace(f"Grabbing new frames...")
                response = self.api_client.get_latest_frames()
                new_frames = MultiFramePayload.parse_obj(response.json())
                self.new_frames(new_frames)
            except Exception as e:
                logger.error(str(e))
                logger.exception(e)
