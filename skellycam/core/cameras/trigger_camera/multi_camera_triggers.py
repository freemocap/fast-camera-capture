import time
from typing import Dict

from pydantic import BaseModel

from skellycam.core import CameraId
from skellycam.core.cameras.config.camera_configs import CameraConfigs
from skellycam.core.cameras.trigger_camera.camera_triggers import SingleCameraTriggers, logger


class MultiCameraTriggers(BaseModel):
    single_camera_triggers: Dict[CameraId, SingleCameraTriggers]

    ##############################################################################################################
    def trigger_multi_frame_read(self):
        self._ensure_cameras_ready()
        # 1 - Trigger each camera should grab an image from the camera device with `cv2.VideoCapture.grab()` (which is faster than `cv2.VideoCapture.read()` as it does not decode the frame)
        self._fire_grab_trigger()

        # 2 - wait for all cameras to grab a frame
        self._await_frame_grabbed()

        # 3- Trigger each camera to retrieve the frame using `cv2.VideoCapture.retrieve()`, which decodes the frame into an image/numpy array
        self._fire_retrieve_trigger()

        # 4 - wait for all cameras to retrieve the frame,
        self._await_frame_retrieved()

        # 5 - wait for the frame to be copied from the `write` buffer to the `read` buffer
        self._await_frame_copied()

        # 5 - Make sure all the triggers are as they should be
        self._verify_hunky_dory_after_read()

    ##############################################################################################################

    @classmethod
    def from_camera_configs(cls, camera_configs: CameraConfigs):
        return cls(
            single_camera_triggers={camera_id: SingleCameraTriggers.from_camera_id(camera_config.camera_id)
                                    for camera_id, camera_config in camera_configs.items()}
        )

    @property
    def cameras_ready(self):
        return all([triggers.camera_ready_event.is_set()
                    for triggers in self.single_camera_triggers.values()])

    @property
    def frame_grabbed(self):
        return not any([triggers.grab_frame_trigger.is_set()
                        for triggers in self.single_camera_triggers.values()])

    @property
    def frame_retrieved(self):
        return not any([triggers.retrieve_frame_trigger.is_set()
                        for triggers in self.single_camera_triggers.values()])

    @property
    def new_frames_available(self):
        return all([triggers.frame_copied_trigger.is_set()
                    for triggers in self.single_camera_triggers.values()])

    def set_frames_copied(self):
        for triggers in self.single_camera_triggers.values():
            triggers.frame_copied_trigger.set()
    def wait_for_cameras_ready(self):
        while not all([triggers.camera_ready_event.is_set() for triggers in self.single_camera_triggers.values()]):
            logger.trace("Waiting for all cameras to be ready...")
            self._wait_very_slow()
        logger.debug("All cameras are ready!")

    def fire_initial_triggers(self):

        self._ensure_cameras_ready()

        logger.debug(f"Firing initial triggers for all cameras...")
        for triggers in self.single_camera_triggers.values():
            triggers.initial_trigger.set()

        logger.trace("Initial triggers set - waiting for all triggers to reset...")
        while any([triggers.initial_trigger.is_set()
                   for triggers in self.single_camera_triggers.values()]):
            self._wait_slow()
        logger.trace("Initial triggers reset!")


    def _fire_grab_trigger(self):
        logger.loop("Triggering all cameras to `grab` a frame...")
        for camera_id, triggers in self.single_camera_triggers.items():
            triggers.grab_frame_trigger.set()

    def _await_frame_grabbed(self):
        while not self.frame_grabbed:
            self._wait_fast()

    def _fire_retrieve_trigger(self):
        logger.loop("Triggering all cameras to `retrieve` that frame...")
        if self.frame_retrieved:
            raise AssertionError("Retrieve triggers are already set!")

        for camera_id, triggers in self.single_camera_triggers.items():
            triggers.retrieve_frame_trigger.set()

    def _await_triggers_reset(self):
        logger.loop("Waiting for triggers to reset...")
        self._wait_for_grab_triggers_reset()
        self._wait_for_frame_grabbed_triggers_reset()
        self._wait_for_retrieve_triggers_reset()
        logger.loop("All triggers reset!")

    def _wait_for_grab_triggers_reset(self):
        while self.grab_triggers_set:
            self._wait_fast()

    def _wait_for_frame_grabbed_triggers_reset(self):
        while self.frame_grabbed:
            self._wait_fast()

    def _wait_for_retrieve_triggers_reset(self):
        while self.frame_retrieved:
            self._wait_fast()

    def _ensure_cameras_ready(self):
        if not self.cameras_ready:
            raise AssertionError("Not all cameras are ready!")

    def _verify_hunky_dory_after_read(self):
        if not all([triggers.camera_ready_event.is_set()
                    for triggers in self.single_camera_triggers.values()]):
            raise AssertionError("Not all cameras are ready!")
        if any([triggers.grab_frame_trigger.is_set()
                for triggers in self.single_camera_triggers.values()]):
            raise AssertionError("Not all `grab` triggers have been reset!")
        if any([triggers.retrieve_frame_trigger.is_set()
                for triggers in self.single_camera_triggers.values()]):
            raise AssertionError("Not all `retrieve` triggers have been reset!")
        if any([triggers.frame_copied_trigger.is_set()
                for triggers in self.single_camera_triggers.values()]):
            raise AssertionError("Not all `frame_copied` triggers have been reset!")

    @staticmethod
    def _wait_very_slow(wait_loop_time: float = 1.0):
        time.sleep(wait_loop_time)

    @staticmethod
    def _wait_slow(wait_loop_time: float = 0.01):
        time.sleep(wait_loop_time)

    @staticmethod
    def _wait_fast(wait_loop_time: float = 0.0001):
        time.sleep(wait_loop_time)
