import logging

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget, QCheckBox

from skellycam.gui.qt.widgets.camera_widgets.camera_panel import SkellycamCameraPanel
from skellycam.gui.qt.widgets.side_panel_widgets.camera_settings_panel import CameraSettingsPanel
from skellycam.skellycam_app.skellycam_app_state import SkellycamAppStateDTO
from skellycam.system.default_paths import CAMERA_WITH_FLASH_EMOJI_STRING, RED_X_EMOJI_STRING, \
    MAGNIFYING_GLASS_EMOJI_STRING, HAMMER_AND_WRENCH_EMOJI_STRING

logger = logging.getLogger(__name__)


class SkellycamCameraControlPanel(QWidget):
    emitting_camera_configs_signal = Signal(dict)

    def __init__(self,
                 camera_panel: SkellycamCameraPanel):
        super().__init__()

        # self.setMinimumWidth(250)

        self.sizePolicy().setVerticalStretch(1)
        self.sizePolicy().setHorizontalStretch(1)

        self._camera_panel = camera_panel
        self.setStyleSheet("""
        QPushButton{
        border-width: 2px;
        font-size: 15px;
        }
        """)

        self._camera_parameter_groups = {}
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        # Make Buttons
        self.detect_available_cameras_button = QPushButton(
            f"Detect Available Cameras {CAMERA_WITH_FLASH_EMOJI_STRING}{MAGNIFYING_GLASS_EMOJI_STRING}")
        self._layout.addWidget(self.detect_available_cameras_button)
        self.detect_available_cameras_button.setEnabled(False)

        # self.connect_cameras_button = QPushButton(
        #     f"Connect Cameras {CAMERA_WITH_FLASH_EMOJI_STRING}{SPARKLES_EMOJI_STRING}")
        # self._layout.addWidget(self.connect_cameras_button)

        self.apply_settings_to_cameras_button = QPushButton(
            f"Apply settings to cameras {CAMERA_WITH_FLASH_EMOJI_STRING}{HAMMER_AND_WRENCH_EMOJI_STRING}",
        )
        self.apply_settings_to_cameras_button.setEnabled(False)
        self._layout.addWidget(self.apply_settings_to_cameras_button)

        self.close_cameras_button = QPushButton(f"Close Cameras {CAMERA_WITH_FLASH_EMOJI_STRING}{RED_X_EMOJI_STRING}")
        self.close_cameras_button.setEnabled(False)
        self._layout.addWidget(self.close_cameras_button)

        # Checkboxes
        self.use_clientside_camera_detection = QCheckBox("Use Client-side Detection")
        self.use_clientside_camera_detection.setChecked(False)
        # self._layout.addWidget(self.use_clientside_camera_detection)
        self.connect_automatically_checkbox = QCheckBox("Connect Automatically")
        self.connect_automatically_checkbox.setChecked(False)
        # self._layout.addWidget(self.connect_automatically_checkbox)
        self.connect_automatically_checkbox = QCheckBox("Use Previous Settings")
        self.connect_automatically_checkbox.setChecked(False)
        # self._layout.addWidget(self.connect_automatically_checkbox)

        # Camera Settings Panel
        self.camera_settings_panel = CameraSettingsPanel(parent=self)
        self._layout.addWidget(self.camera_settings_panel)

    @property
    def user_selected_camera_configs(self):
        return self.camera_settings_panel.user_selected_camera_configs

    @Slot(object)
    def handle_new_app_state(self, app_state: SkellycamAppStateDTO):
        if app_state.camera_configs:
            self.apply_settings_to_cameras_button.setEnabled(True)
            self.camera_settings_panel.update_camera_configs(available_devices=app_state.available_devices,
                                                             camera_configs=app_state.camera_configs)
        else:
            self.apply_settings_to_cameras_button.setEnabled(False)

        if app_state.camera_configs:
            self.close_cameras_button.setEnabled(True)
        else:
            self.close_cameras_button.setEnabled(False)
