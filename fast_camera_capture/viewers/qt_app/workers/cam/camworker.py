import logging
import time
from copy import deepcopy
from multiprocessing import Process
from pathlib import Path
from typing import List, Union, Dict

import cv2
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QImage

from fast_camera_capture.detection.models.frame_payload import FramePayload
from fast_camera_capture.opencv.camera.types.camera_id import CameraId
from fast_camera_capture.opencv.group.camera_group import CameraGroup
from fast_camera_capture.opencv.video_recorder.save_synchronized_videos import save_synchronized_videos
from fast_camera_capture.opencv.video_recorder.video_recorder import VideoRecorder

logger = logging.getLogger(__name__)


class CamGroupFrameWorker(QThread):
    ImageUpdate = pyqtSignal(CameraId, QImage)
    cameras_connected_signal = pyqtSignal()
    save_videos_signal = pyqtSignal(dict, str, bool)

    def __init__(self,
                 camera_ids: Union[List[str], None],
                 session_folder_path: Union[str, Path] = None,
                 parent=None):

        self._video_save_process = None
        logger.info(f"Initializing camera group frame worker with camera ids: {camera_ids}")
        super().__init__(parent=parent)

        try:
            self._session_folder_path = Path(session_folder_path)
        except TypeError:
            self._session_folder_path = None

        self._should_pause_bool = False
        self._should_record_frames_bool = True
        self._camera_ids = camera_ids

        if self._camera_ids is not None:
            self._camera_group = CameraGroup(camera_ids)
            self._video_recorder_dictionary = self._initialize_video_recorder_dictionary()
        else:
            self._camera_group = None
            self._video_recorder_dictionary = None

    @property
    def camera_ids(self):
        return self._camera_ids

    @camera_ids.setter
    def camera_ids(self, camera_ids: List[str]):
        self._camera_ids = camera_ids

        if self._camera_ids is not None:
            if self._camera_group is not None:
                while self._camera_group.is_capturing:
                    self._camera_group.close()
                    time.sleep(0.1)

        self._camera_group = CameraGroup(camera_ids)
        self._video_recorder_dictionary = self._initialize_video_recorder_dictionary()

    @property
    def slot_dictionary(self):
        """
        dictionary of slots to attach to signals in QtMultiCameraControllerWidget
        NOTE - `keys` must match those in QtMultiCameraControllerWidget.button_dictionary
        """
        return {
            "play": self.play,
            "pause": self.pause,
            "start_recording": self.start_recording,
            "stop_recording": self.stop_recording,

        }

    def run(self):
        logger.info("Starting camera group frame worker")
        self._camera_group.start()
        self._recording_id = self._generate_recording_id()
        should_continue = True
        self.cameras_connected_signal.emit()
        while self._camera_group.is_capturing and should_continue:

            frame_obj = self._camera_group.latest_frames()
            for camera_id, frame in frame_obj.items():
                if frame:

                    if self._should_pause_bool:
                        continue

                    if self._should_record_frames_bool:
                        self._video_recorder_dictionary[camera_id].append_frame_payload_to_list(frame)

                    print(f"frame number: {self._video_recorder_dictionary[camera_id].number_of_frames}")

                    qimage = self._convert_frame(frame)
                    self.ImageUpdate.emit(camera_id, qimage)

    def _convert_frame(self, frame: FramePayload):
        image = frame.image
        # image = cv2.flip(image, 1)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        converted_frame = QImage(
            image.data,
            image.shape[1],
            image.shape[0],
            QImage.Format.Format_RGB888,
        )
        return converted_frame.scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio)

    def close(self):
        logger.info("Closing camera group")
        self._camera_group.close()

    def pause(self):
        logger.info("Pausing image display")
        self._should_pause_bool = True

    def play(self):
        logger.info("Resuming image display")
        self._should_pause_bool = False

    def start_recording(self):
        logger.info("Starting recording")
        self._should_record_frames_bool = True

    def stop_recording(self):
        logger.info("Stopping recording")
        self._should_record_frames_bool = False

        recording_folder_path_string = str(Path(self._session_folder_path / self._recording_id))
        logger.info(f"Emitting save_videos_signal with recording_folder_path_string: {recording_folder_path_string}")
        self.save_videos_signal.emit(self._video_recorder_dictionary, recording_folder_path_string, True)

    def _launch_save_video_process(self):
        logger.info("Launching save video process")
        if self._video_save_process is not None:
            while self._video_save_process.is_alive():
                time.sleep(0.1)
                logger.info(f"Waiting for video save process to finish: {self._video_save_process}")

        recording_folder_path_string = str(Path(self._session_folder_path / self._recording_id))
        self._video_save_process = Process(
            name=f"VideoSaveProcess",
            target=save_synchronized_videos,
            args=(deepcopy(self._video_recorder_dictionary), recording_folder_path_string, True),
        )
        self._video_save_process.start()

    def _initialize_video_recorder_dictionary(self):
        return {camera_id: VideoRecorder() for camera_id in self._camera_ids}

    def _generate_recording_id(self) -> str:
        return time.strftime("%H_%M_%S_recording")
