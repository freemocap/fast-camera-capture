import logging
import multiprocessing
from pathlib import Path
from typing import Union

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDockWidget, QMainWindow, QVBoxLayout, QWidget

from skellycam.gui import get_client, shutdown_client_server
from skellycam.gui.qt.css.qt_css_stylesheet import QT_CSS_STYLE_SHEET_STRING
from skellycam.gui.qt.skelly_cam_widget import (
    SkellyCamWidget,
)
from skellycam.gui.qt.widgets.side_panel_widgets.skellycam_side_panel import (
    SkellyCamControlPanel,
)
from skellycam.gui.qt.widgets.skellycam_directory_view import SkellyCamDirectoryViewWidget
from skellycam.gui.qt.widgets.skellycam_record_buttons_panel import (
    SkellyCamRecordButtonsPanel,
)
from skellycam.gui.qt.widgets.welcome_to_skellycam_widget import (
    WelcomeToSkellyCamWidget,
)
from skellycam.system.default_paths import get_default_skellycam_base_folder_path, create_default_recording_folder_path, \
    create_new_synchronized_videos_folder, default_recording_name, PATH_TO_SKELLY_CAM_LOGO_SVG

logger = logging.getLogger(__name__)


class SkellyCamMainWindow(QMainWindow):

    def __init__(self,
                 session_folder_path: Union[str, Path] = None,
                 shutdown_event: multiprocessing.Event = None,
                 parent=None):
        super().__init__(parent=parent)
        if session_folder_path is None:
            self._session_folder_path = create_default_recording_folder_path()
        else:
            self._session_folder_path = session_folder_path

        self._base_folder_path = get_default_skellycam_base_folder_path()

        self._shutdown_event = shutdown_event
        self.initUI()
        self.client = get_client()
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
        self._skellycam_widget = SkellyCamWidget(
            get_new_synchronized_videos_folder_callable=
            lambda: create_new_synchronized_videos_folder(
                Path(self._session_folder_path) / default_recording_name()
            ),
            parent=self
        )
        self._skellycam_widget.resize(1280, 720)
        self._skellycam_record_buttons = SkellyCamRecordButtonsPanel(
            skellycam_widget=self._skellycam_widget,
            parent=self,
        )
        self._layout.addWidget(self._skellycam_record_buttons)
        self._layout.addWidget(self._skellycam_widget)
        self._parameter_tree_dock_widget = QDockWidget("Camera Settings", self)
        self._parameter_tree_dock_widget.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable,
        )
        self.skellycam_control_panel = (
            SkellyCamControlPanel(self._skellycam_widget)
        )
        # self._layout.addWidget(self._qt_camera_config_parameter_tree_widget)
        self._parameter_tree_dock_widget.setWidget(
            self.skellycam_control_panel
        )
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self._parameter_tree_dock_widget
        )
        self._directory_view_dock_widget = QDockWidget("Directory View", self)
        self._directory_view_widget = SkellyCamDirectoryViewWidget(
            folder_path=self._base_folder_path
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
        self._skellycam_widget.gui_state_changed.connect(self.skellycam_control_panel.update)

        self._skellycam_widget.detect_available_cameras_push_button.clicked.connect(
            self._welcome_to_skellycam_widget.hide
        )

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
