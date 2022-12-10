import asyncio
import logging
import multiprocessing
import time
from typing import List, Dict

from fast_camera_capture import WebcamConfig
from fast_camera_capture.detection.detect_cameras import detect_cameras
from fast_camera_capture.experiments.cam_show import cam_show
from fast_camera_capture.opencv.group.strategies.grouped_process_strategy import (
    GroupedProcessStrategy,
)
from fast_camera_capture.opencv.group.strategies.strategies import Strategy

logger = logging.getLogger(__name__)


class CameraGroup:
    def __init__(
        self,
        cam_ids: List[str],
        strategy: Strategy = Strategy.X_CAM_PER_PROCESS,
        webcam_config_dict: Dict[str, WebcamConfig] = None,
    ):
        self._event_dictionary = None
        self._strategy_enum = strategy
        self._cam_ids = cam_ids

        # Make optional, if a list of cams is sent then just use that
        if not cam_ids:
            _cams = detect_cameras()
            cam_ids = _cams.cameras_found_list
        self._strategy_class = self._resolve_strategy(cam_ids)

        if webcam_config_dict is None:
            self._webcam_config_dict = {}
            for cam_id in cam_ids:
                self._webcam_config_dict[cam_id] = WebcamConfig()
        else:
            self._webcam_config_dict = webcam_config_dict

    @property
    def is_capturing(self):
        return self._strategy_class.is_capturing

    @property
    def exit_event(self):
        return self._exit_event

    def start(self):
        """
        Creates new processes to manage cameras. Use the `get` API to grab camera frames
        :return:
        """
        self._exit_event = multiprocessing.Event()
        self._start_event = multiprocessing.Event()
        self._event_dictionary = {"start": self._start_event, "exit": self._exit_event}
        self._strategy_class.start_capture(
            event_dictionary=self._event_dictionary,
            webcam_config_dict=self._webcam_config_dict,
        )

        self._wait_for_cameras_to_start()

    def _wait_for_cameras_to_start(self, restart_process_if_it_dies: bool = True):
        logger.info(f"Waiting for cameras {self._cam_ids} to start")
        all_cameras_started = False
        while not all_cameras_started:
            time.sleep(0.5)
            camera_started_dictionary = dict.fromkeys(self._cam_ids, False)

            for camera_id in self._cam_ids:
                camera_started_dictionary[camera_id] = self.check_if_camera_is_ready(
                    camera_id
                )

            logger.debug(f"Camera started? {camera_started_dictionary}")

            logger.debug(f"Active processes { multiprocessing.active_children()}")
            if restart_process_if_it_dies:
                self._restart_dead_processes()

            all_cameras_started = all(list(camera_started_dictionary.values()))

        logger.info(f"All cameras {self._cam_ids} started!")
        self._start_event.set()  # start frame capture on all cameras

    def check_if_camera_is_ready(self, cam_id: str):
        return self._strategy_class.check_if_camera_is_ready(cam_id)

    def get_by_cam_id(self, cam_id: str):
        return self._strategy_class.get_by_cam_id(cam_id)

    def latest_frames(self):
        return self._strategy_class.get_latest_frames()

    def _resolve_strategy(self, cam_ids: List[str]):
        if self._strategy_enum == Strategy.X_CAM_PER_PROCESS:
            return GroupedProcessStrategy(cam_ids)

    def close(self, wait_for_exit: bool = True):
        logger.info("Closing camera group")
        self._set_exit_event()
        self._terminate_processes()

        if wait_for_exit:
            while self.is_capturing:
                logger.debug("waiting for camera group to stop....")
                time.sleep(0.1)

    def _set_exit_event(self):
        logger.info("Setting exit event")
        self.exit_event.set()

    def _terminate_processes(self):
        logger.info("Terminating processes")
        for cam_group_process in self._strategy_class._processes:
            logger.info(f"Terminating process - {cam_group_process.name}")
            cam_group_process.terminate()

    def _restart_dead_processes(self):
        active_processes = multiprocessing.active_children()
        active_process_names = [process.name for process in active_processes]
        for process in self._strategy_class.processes:
            if process.name not in active_process_names:
                logger.info(f"Process {process.name} died! Restarting now...")
                process.start_capture(
                    event_dictionary=self._event_dictionary,
                    webcam_config_dict=self._webcam_config_dict,
                )


# async def getall(g: CameraGroup):
#     await asyncio.gather(
#         cam_show("0", lambda: g.get_by_cam_id("0")),
#         cam_show("2", lambda: g.get_by_cam_id("2")),
#     )
#
#
# if __name__ == "__main__":
#     cams = ["0"]
#     g = CameraGroup(cams)
#     g.start()
#
#     asyncio.run(getall(g))
