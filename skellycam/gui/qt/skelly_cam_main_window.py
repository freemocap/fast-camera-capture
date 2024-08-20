import logging
import multiprocessing
from pathlib import Path
from typing import Union

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDockWidget, QMainWindow, QVBoxLayout, QWidget

from skellycam.gui import shutdown_client_server
from skellycam.gui.gui_state import get_gui_state
from skellycam.gui.qt.css.qt_css_stylesheet import QT_CSS_STYLE_SHEET_STRING
from skellycam.gui.qt.skelly_cam_widget import (
    SkellyCamWidget,
)
from skellycam.gui.qt.widgets.connect_to_cameras_button import ConnectToCamerasButton
from skellycam.gui.qt.widgets.side_panel_widgets.skellycam_side_panel import (
    SkellyCamControlPanel,
)
from skellycam.gui.qt.widgets.skellycam_directory_view import SkellyCamDirectoryViewWidget
from skellycam.gui.qt.widgets.welcome_to_skellycam_widget import (
    WelcomeToSkellyCamWidget,
)
from skellycam.system.default_paths import get_default_skellycam_base_folder_path, PATH_TO_SKELLY_CAM_LOGO_SVG, \
    get_default_skellycam_recordings_path

logger = logging.getLogger(__name__)


class SkellyCamMainWindow(QMainWindow):

    def __init__(self,
                 shutdown_event: multiprocessing.Event = None,
                 parent=None):
        super().__init__(parent=parent)
        self._shutdown_event = shutdown_event
        self.initUI()
        self._gui_state = get_gui_state()
        self._connect_signals_to_slots()

    def initUI(self):
        self.setGeometry(100, 100, 1600, 900)
        self.setWindowIcon(QIcon(PATH_TO_SKELLY_CAM_LOGO_SVG))
        self.setStyleSheet(QT_CSS_STYLE_SHEET_STRING)
        self.setWindowTitle("Skelly Cam \U0001F480 \U0001F4F8")
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        self._layout = QVBoxLayout()
        self._central_widget.setLayout(self._layout)

        self._welcome_to_skellycam_widget = WelcomeToSkellyCamWidget()
        self._layout.addWidget(self._welcome_to_skellycam_widget)

        self._connect_to_cameras_button = ConnectToCamerasButton(parent=self)
        self._layout.addWidget(self._connect_to_cameras_button)

        self._skellycam_widget = SkellyCamWidget(parent=self)
        self._skellycam_widget.hide()
        self._layout.addWidget(self._skellycam_widget)

        self._parameter_tree_dock_widget = QDockWidget("Camera Settings", self)
        self._parameter_tree_dock_widget.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable,
        )
        self.skellycam_control_panel = (
            SkellyCamControlPanel(self._skellycam_widget)
        )
        self._parameter_tree_dock_widget.setWidget(
            self.skellycam_control_panel
        )
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self._parameter_tree_dock_widget
        )
        self._directory_view_dock_widget = QDockWidget("Directory View", self)
        self._directory_view_widget = SkellyCamDirectoryViewWidget(
            folder_path=get_default_skellycam_recordings_path()
        )
        self._directory_view_dock_widget.setWidget(self._directory_view_widget)
        self._directory_view_dock_widget.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable,
        )
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self._directory_view_dock_widget
        )
        self.tabifyDockWidget(
            self._directory_view_dock_widget,
            self._parameter_tree_dock_widget,
        )

    def _connect_signals_to_slots(self):

        self._skellycam_widget.devices_detected.connect(self.skellycam_control_panel.update_parameter_tree)
        self._skellycam_widget.cameras_connected.connect(
            self._skellycam_widget.camera_view_grid.create_single_camera_views)
        self._skellycam_widget.new_frames_available.connect(self._skellycam_widget.recording_panel.update)
        self._skellycam_widget.new_frames_available.connect(
            self._skellycam_widget.camera_view_grid.handle_new_frontend_payload)

        self._skellycam_widget.new_frames_available.connect(
            self._skellycam_widget.recording_panel.update_recording_info)

        self._connect_to_cameras_button.button.clicked.connect(
            self._welcome_to_skellycam_widget.hide
        )
        self._connect_to_cameras_button.button.clicked.connect(
            self._connect_to_cameras_button.hide
        )
        self._connect_to_cameras_button.button.clicked.connect(
            self._skellycam_widget.show
        )
        self._connect_to_cameras_button.button.clicked.connect(self._skellycam_widget.connect_to_cameras)

    def _handle_videos_saved_to_this_folder(self, folder_path: Union[str, Path]):
        logger.debug(f"Recieved `videos_saved_to_this_folder` signal with string:  {folder_path}")
        self._directory_view_widget.expand_directory_to_path(folder_path)

    def closeEvent(self, a0) -> None:

        # remove_empty_directories(get_default_skellycam_base_folder_path())

        try:
            self._skellycam_widget.close()
        except Exception as e:
            logger.error(f"Error while closing the viewer widget: {e}")
        super().closeEvent(a0)

        logger.info("Shutting down client server...")
        shutdown_client_server()
        self._shutdown_event.set()
        remove_empty_directories(get_default_skellycam_base_folder_path())



def remove_empty_directories(root_dir: Union[str, Path]):
    """
    Recursively remove empty directories from the root directory
    :param root_dir: The root directory to start removing empty directories from
    """
    for path in Path(root_dir).rglob("*"):
        if path.is_dir() and not any(path.iterdir()):
            logger.info(f"Removing empty directory: {path}")
            path.rmdir()
        elif path.is_dir() and any(path.iterdir()):
            remove_empty_directories(path)
        else:
            continue


if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    main_window = SkellyCamMainWindow()
    main_window.show()
    app.exec()
    for process in multiprocessing.active_children():
        logger.info(f"Terminating process: {process}")
        process.terminate()
    sys.exit()
