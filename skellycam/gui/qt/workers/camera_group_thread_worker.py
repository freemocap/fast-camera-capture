import logging
import multiprocessing
from pathlib import Path
from typing import List, Union, Dict

from PyQt6.QtCore import pyqtSignal, QThread

from skellycam import CameraConfig
from skellycam.opencv.group.camera_group import CameraGroup

logger = logging.getLogger(__name__)


class CamGroupThreadWorker(QThread):
    new_image_signal = pyqtSignal(dict)
    cameras_connected_signal = pyqtSignal()
    cameras_closed_signal = pyqtSignal()
    camera_group_created_signal = pyqtSignal(dict)
    videos_saved_to_this_folder_signal = pyqtSignal(str)

    def __init__(
        self,
        camera_ids: List[str],
        camera_configs: Dict[str, CameraConfig],
        get_new_synchronized_videos_folder: callable,
        parent=None,
    ):
        logger.info(
            f"Initializing camera group frame worker with camera ids: {camera_ids}"
        )
        super().__init__(parent=parent)
        self._camera_ids = camera_ids
        self._get_new_synchronized_videos_folder = get_new_synchronized_videos_folder

        self._current_recording_name = None
        self._video_save_process = None

        self._camera_group = self._create_camera_group(
            camera_ids=self._camera_ids, camera_configs=camera_configs
        )

    @property
    def camera_ids(self):
        return self._camera_ids

    @property
    def cameras_connected(self):
        return self._camera_group.is_capturing

    @property
    def is_recording(self):
        return self._camera_group.should_record_frames_event.is_set()

    def run(self):
        logger.info("Starting camera group thread worker")
        self._camera_group.start_capture()
        should_continue = True

        logger.info("Emitting `cameras_connected_signal`")
        self.cameras_connected_signal.emit()

        while self._camera_group.is_capturing and should_continue:
            frame_payload_dictionary = self._camera_group.latest_frames
            if frame_payload_dictionary is None:
                logger.warning("No frames received from camera group")
                continue
            self.new_image_signal.emit(frame_payload_dictionary)

    def close(self):
        logger.info("Closing camera group")
        try:
            self._camera_group.close(cameras_closed_signal=self.cameras_closed_signal)
        except AttributeError:
            pass

    def play(self):
        logger.info("Resuming image display")
        self._should_pause_bool = False

    def start_recording(self):
        logger.info("Starting recording")
        video_file_paths = {camera_id: str(Path(self._get_new_synchronized_videos_folder()) / f"camera_{camera_id}.mp4")
                            for camera_id in self._camera_ids}

        if self.cameras_connected:
            logger.debug("Starting recording")
            self._camera_group.start_recording(video_save_paths=video_file_paths)
        else:
            logger.warning("Cannot start recording - cameras not connected")

    def stop_recording(self):
        logger.info("Stopping recording")
        if self.cameras_connected:
            self._camera_group.stop_recording()
        else:
            logger.warning("Cannot stop recording - cameras not connected")


    def update_camera_configs(self, camera_configs: Dict[str, CameraConfig]):
        self._camera_group.update_camera_configs(camera_configs=camera_configs)

    def _create_camera_group(
        self, camera_ids: List[Union[str, int]], camera_configs: dict
    ):
        logger.info(
            f"Creating `camera_group` for camera_ids: {camera_ids}, camera_config_dictionary: {camera_configs}"
        )

        camera_group = CameraGroup(
            camera_ids=camera_ids,
        )

        return camera_group
