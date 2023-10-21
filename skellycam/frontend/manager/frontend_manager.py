import multiprocessing
from typing import TYPE_CHECKING, Dict

from skellycam import logger
from skellycam.backend.controller.interactions.base_models import BaseResponse
from skellycam.backend.controller.interactions.close_cameras import CloseCamerasInteraction, CloseCamerasResponse
from skellycam.backend.controller.interactions.connect_to_cameras import ConnectToCamerasInteraction, \
    ConnectToCamerasResponse
from skellycam.backend.controller.interactions.detect_available_cameras import CamerasDetectedResponse, \
    DetectCamerasInteraction
from skellycam.backend.controller.interactions.update_camera_configs import UpdateCameraConfigsInteraction
from skellycam.frontend.manager.helpers.frame_grabber import FrameGrabber
from skellycam.models.cameras.camera_config import CameraConfig
from skellycam.models.cameras.camera_id import CameraId

if TYPE_CHECKING:
    from skellycam.frontend.gui.main_window.main_window import MainWindow
    from skellycam.frontend.gui.widgets.camera_control_panel import CameraControlPanel
    from skellycam.frontend.gui.widgets.camera_views.camera_grid import CameraGrid
    from skellycam.frontend.gui.widgets.camera_parameter_tree import CameraParameterTree
    from skellycam.frontend.gui.widgets.record_buttons import RecordButtons
    from skellycam.frontend.gui.widgets.welcome import Welcome


class FrontendManager:
    def __init__(self,
                 main_window: 'MainWindow',
                 frontend_frame_pipe_receiver  # multiprocessing.connection.Connection
                 ) -> None:
        self.main_window = main_window
        self._stop_frame_grabber_event = multiprocessing.Event()
        self._frame_grabber = FrameGrabber(parent=self.main_window,
                                           stop_event=self._stop_frame_grabber_event,
                                           frontend_frame_pipe_receiver=frontend_frame_pipe_receiver)

        self._connect_signals()

    def handle_backend_response(self, response: BaseResponse) -> None:
        logger.trace(f"Updating view with message type: {response}")

        if isinstance(response, CamerasDetectedResponse):
            self._handle_cameras_detected_response(response)
        elif isinstance(response, ConnectToCamerasResponse):
            self._handle_cameras_connected_response()
        elif isinstance(response, CloseCamerasResponse):
            self._handle_cameras_closed_response()
        elif isinstance(response, BaseResponse):
            logger.warning(f"Received BaseResponse with no 'response' behavior: {response}")
        else:
            raise ValueError(f"Unhandled response type: {response}")

    @property
    def welcome(self) -> 'Welcome':
        return self.main_window.welcome

    @property
    def camera_grid(self) -> 'CameraGrid':
        return self.main_window.camera_grid

    @property
    def record_buttons(self) -> 'RecordButtons':
        return self.main_window.record_buttons

    @property
    def camera_parameter_tree(self) -> 'CameraParameterTree':
        return self.main_window.camera_parameter_tree

    @property
    def camera_control_panel(self) -> 'CameraControlPanel':
        return self.main_window.camera_control_panel

    @property
    def camera_configs(self) -> Dict[CameraId, CameraConfig]:
        return self.camera_parameter_tree.camera_configs

    def _connect_signals(self) -> None:
        self.welcome.start_session_button.clicked.connect(self._handle_start_session_signal)

        self.camera_parameter_tree.camera_configs_changed.connect(
            self._handle_camera_configs_changed)

        self.camera_control_panel.close_cameras_button.clicked.connect(
            self._emit_close_cameras_interaction)

        self.camera_control_panel.connect_to_cameras_button.clicked.connect(
            self._emit_connect_to_cameras_interaction)

        self.camera_control_panel.detect_available_cameras_button.clicked.connect(
            self._emit_detect_cameras_interaction)

        self._frame_grabber.new_frames.connect(self.camera_grid.handle_new_images)

    def _handle_cameras_detected_response(self, response: CamerasDetectedResponse):
        self.camera_control_panel.handle_cameras_detected()
        self.camera_parameter_tree.update_available_cameras(available_cameras=response.available_cameras)
        self.camera_grid.update_camera_grid(camera_configs=self.camera_configs)

    def _handle_start_session_signal(self):
        self.main_window.welcome.hide()
        self.main_window.camera_grid.show()
        self.main_window.record_buttons.show()
        self.main_window.camera_settings_dock.show()
        self._emit_detect_cameras_interaction()

    def _handle_camera_configs_changed(self, camera_configs: Dict[CameraId, CameraConfig]):
        logger.info("Handling Camera Configs Changed signal")

        self.camera_grid.update_camera_grid(camera_configs=camera_configs)
        self.main_window.interact_with_backend.emit(
            UpdateCameraConfigsInteraction.as_request(camera_configs=self.camera_configs))

    def _emit_detect_cameras_interaction(self):
        logger.info("Emitting detect cameras interaction")
        self.main_window.interact_with_backend.emit(DetectCamerasInteraction.as_request())

    def _emit_close_cameras_interaction(self):
        logger.info("Emitting close cameras interaction")
        self._stop_frame_grabber_event.set()
        self.main_window.interact_with_backend.emit(CloseCamerasInteraction.as_request())

    def _emit_connect_to_cameras_interaction(self):
        logger.info("Emitting connect to cameras interaction")
        self.main_window.interact_with_backend.emit(
            ConnectToCamerasInteraction.as_request(camera_configs=self.camera_configs))

        self._start_frame_grabber()

    def _start_frame_grabber(self):
        self._stop_frame_grabber_event.clear()
        self._frame_grabber.start()

    def _handle_cameras_connected_response(self):
        self.camera_control_panel.close_cameras_button.setEnabled(True)

    def _handle_cameras_closed_response(self):
        self.camera_control_panel.handle_cameras_closed()
