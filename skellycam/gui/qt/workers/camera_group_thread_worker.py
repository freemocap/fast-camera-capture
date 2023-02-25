import logging
import multiprocessing
import time
from copy import deepcopy
from multiprocessing.managers import DictProxy

from pathlib import Path
from typing import List, Union, Dict

from PyQt6.QtCore import pyqtSignal, QThread

from skellycam.gui.qt.workers.video_save_thread_worker import VideoSaveThreadWorker
from skellycam.opencv.group.camera_group import CameraGroup
from skellycam.opencv.video_recorder.video_recorder import VideoRecorder

logger = logging.getLogger(__name__)


class CamGroupThreadWorker(QThread):
    new_image_signal = pyqtSignal(dict)
    cameras_connected_signal = pyqtSignal()
    cameras_closed_signal = pyqtSignal()
    camera_group_created_signal = pyqtSignal(dict)
    videos_saved_to_this_folder_signal = pyqtSignal(str)

    def __init__(
            self,
            camera_ids: Union[List[str], None],
            get_new_synchronized_videos_folder_callable: callable,
            parent=None,
    ):

        self._synchronized_video_folder_path = None
        logger.info(
            f"Initializing camera group frame worker with camera ids: {camera_ids}"
        )
        super().__init__(parent=parent)
        self._camera_ids = camera_ids
        self._get_new_synchronized_videos_folder_callable = get_new_synchronized_videos_folder_callable

        self._updating_camera_settings_bool = False
        self._current_recording_name = None
        self._video_save_process = None

        if self._camera_ids is not None:
            self._camera_group = self._create_camera_group(self._camera_ids)
            self._video_recorder_dictionary = (
                self._initialize_video_recorder_dictionary()
            )
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

        self._camera_group = self._create_camera_group(self._camera_ids)
        self._video_recorder_dictionary = self._initialize_video_recorder_dictionary()

    @property
    def slot_dictionary(self):
        """
        dictionary of slots to attach to signals in QtMultiCameraControllerWidget
        NOTE - `keys` must match those in QtMultiCameraControllerWidget.button_dictionary
        """
        return {
            "play": self.play,
            "start_recording": self.start_recording,
            "stop_recording": self.stop_recording,
        }

    @property
    def camera_config_dictionary(self):
        return self._camera_group.camera_config_dictionary

    @property
    def cameras_connected(self):
        return self._camera_group.is_capturing

    @property
    def is_recording(self):
        return self._camera_group.recording_frames

    @property
    def frame_list_lengths(self) -> Dict[str, int]:
        return self._camera_group.frame_list_lengths

    def run(self):
        logger.info("Starting camera group thread worker")
        self._camera_group.start()
        should_continue = True

        logger.info("Emitting `cameras_connected_signal`")
        self.cameras_connected_signal.emit()

        while self._camera_group.is_capturing and should_continue:
            if self._updating_camera_settings_bool:
                continue

            frame_payload_dictionary = dict(self._camera_group.latest_frames)
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
        if self.cameras_connected:
            if self._synchronized_video_folder_path is None:
                self._synchronized_video_folder_path = self._get_new_synchronized_videos_folder_callable()


            for camera_id in self._camera_group.video_save_paths_by_camera.keys():
                video_file_name = str(Path(self._synchronized_video_folder_path) / f"Camera_{camera_id}_synchronized.mp4")
                self._camera_group.video_save_paths_by_camera[camera_id] = video_file_name

            self._camera_group.recording_frames = True
        else:
            logger.warning("Cannot start recording - cameras not connected")

    def stop_recording(self):
        logger.info("Stopping recording")
        self._camera_group.recording_frames = False


    def update_camera_group_configs(self, camera_config_dictionary: dict):
        if self._camera_ids is None:
            self._camera_ids = list(camera_config_dictionary.keys())

        if self._camera_group is None:
            self._camera_group = self._create_camera_group(
                camera_ids=self.camera_ids,
                camera_config_dictionary=camera_config_dictionary,
            )
            return

        self._updating_camera_settings_bool = True
        self._updating_camera_settings_bool = not self._update_camera_settings(
            camera_config_dictionary
        )

    def _launch_save_video_thread_worker(self):
        logger.info("Launching save video thread worker")

        synchronized_videos_folder = self._synchronized_video_folder_path
        self._synchronized_video_folder_path = None

        self._video_save_thread_worker = VideoSaveThreadWorker(
            dictionary_of_video_recorders=deepcopy(self._video_recorder_dictionary),
            folder_to_save_videos=str(synchronized_videos_folder),
            create_diagnostic_plots_bool=True,
        )
        self._video_save_thread_worker.start()
        self._video_save_thread_worker.finished_signal.connect(
            self._handle_videos_save_thread_worker_finished
        )

    def _handle_videos_save_thread_worker_finished(self, folder_path: str):
        logger.debug(f"Emitting `videos_saved_to_this_folder_signal` with string: {folder_path}")
        self.videos_saved_to_this_folder_signal.emit(folder_path)

    #
    # def _launch_save_video_process(self):
    #     logger.info("Launching save video process")
    #     if self._video_save_process is not None:
    #         while self._video_save_process.is_alive():
    #             time.sleep(0.1)
    #             logger.info(
    #                 f"Waiting for video save process to finish: {self._video_save_process}"
    #             )
    #
    #     synchronized_videos_folder = self._synchronized_video_folder_path
    #     self._synchronized_video_folder_path = None
    #     self._video_save_process = Process(
    #         name=f"VideoSaveProcess",
    #         target=save_synchronized_videos,
    #         args=(
    #             deepcopy(self._video_recorder_dictionary),
    #             synchronized_videos_folder,
    #             True,
    #             self.videos_saved_to_this_folder_signal
    #         ),
    #     )
    #     logger.info(f"Launching video save process: {self._video_save_process}")
    #
    #     self._video_save_process.start()
    #     self._video_save_thread_worker.finished_signal.connect(
    #         lambda: self.videos_saved_to_this_folder_signal.emit
    #     )

    def _initialize_video_recorder_dictionary(self):
        return {camera_id: VideoRecorder() for camera_id in self._camera_ids}

    def _get_recorder_frame_count_dict(self):
        return {
            camera_id: recorder.number_of_frames
            for camera_id, recorder in self._video_recorder_dictionary.items()
        }

    def _create_camera_group(
            self, camera_ids: List[Union[str, int]], camera_config_dictionary: dict = None
    ):
        logger.info(
            f"Creating `camera_group` for camera_ids: {camera_ids}, camera_config_dictionary: {camera_config_dictionary}"
        )

        camera_group = CameraGroup(
            camera_ids_list=camera_ids,
            camera_config_dictionary=camera_config_dictionary,
        )
        self.camera_group_created_signal.emit(camera_group.camera_config_dictionary)
        return camera_group

    def _update_camera_settings(self, camera_config_dictionary: dict):
        try:
            self._camera_group.update_camera_configs(camera_config_dictionary)

        except Exception as e:
            logger.error(f"Problem updating camera settings: {e}")

        return True
