import logging
import multiprocessing
from asyncio import Future
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Callable

from pydantic import BaseModel, ConfigDict, Field

from skellycam.core.camera_group.camera.config.camera_config import CameraConfigs
from skellycam.core.camera_group.camera.config.update_instructions import UpdateInstructions
from skellycam.core.playback.video_config import load_video_configs_from_folder
from skellycam.core.recorders.start_recording_request import StartRecordingRequest
from skellycam.skellycam_app.skellycam_app_state import SkellycamAppState, create_skellycam_app_state
from skellycam.system.device_detection.detect_available_cameras import get_available_cameras, CameraDetectionStrategies

logger = logging.getLogger(__name__)


class ControllerThreadManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor()
        self._connect_to_cameras_task: Optional[Future] = None
        self._detect_available_cameras_task: Optional[Future] = None
        self._update_camera_configs_task: Optional[Future] = None
        self._read_videos_task: Optional[Future] = None

    def submit_task(self, task_name: str, task_callable: Callable, *args, **kwargs):
        if getattr(self, f"_{task_name}_task") is None or getattr(self, f"_{task_name}_task").done():
            future = self.executor.submit(task_callable, *args, **kwargs)
            setattr(self, f"_{task_name}_task", future)
            logger.debug(f"Submitted `{task_name}` task: " + str(future))
        else:
            logger.warning(f"{task_name} task already running! Ignoring request...")


class SkellycamAppController(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    app_state: SkellycamAppState
    tasks: ControllerThreadManager = Field(default_factory=ControllerThreadManager)

    @classmethod
    def create(cls,
               skellycam_app_state: SkellycamAppState):
        return cls(app_state=skellycam_app_state)

    def detect_available_cameras(self):
        # TODO - deprecate `/camreas/detect/` route and move 'detection' responsibilities to client?
        logger.info(f"Detecting available cameras...")

        self.tasks.submit_task("detect_available_cameras", self._detect_available_cameras)

    def connect_to_cameras(self, camera_configs: Optional[CameraConfigs] = None):
        try:
            if camera_configs and self.app_state.camera_group:
                # if CameraGroup already exists, check if new configs require reset
                update_instructions = UpdateInstructions.from_configs(new_configs=camera_configs,
                                                                      old_configs=self.app_state.camera_group_configs)
                if not update_instructions.reset_all:
                    # Update instructions do not require reset - update existing camera group
                    logger.debug(f"Updating CameraGroup with configs: {camera_configs}")
                    self.app_state.update_camera_group(camera_configs=camera_configs,
                                                       update_instructions=update_instructions)
                    return

                # Update instructions require reset - close existing group (will be re-created below)
                logger.debug(f"Updating CameraGroup requires reset - closing existing group and reconnecting...")

            logger.info(f"Connecting to cameras....")
            self.tasks.submit_task("connect_to_cameras", self._create_camera_group, camera_configs=camera_configs)
        except Exception as e:
            logger.exception(f"Error connecting to cameras: {e}")
            raise

    def start_recording(self, request: StartRecordingRequest):
        logger.info("Starting recording...")
        self.app_state.start_recording(request)

    def stop_recording(self):
        logger.info("Starting recording...")
        self.app_state.stop_recording()

    def _create_camera_group(self, camera_configs: CameraConfigs):
        try:

            if not self.app_state.available_cameras and not camera_configs:
                self._detect_available_cameras(strategy=CameraDetectionStrategies.OPENCV)
                if not self.app_state.available_cameras:
                    logger.warning("No available devices detected!")
                    return
                camera_configs = self.app_state.camera_group_configs

            if self.app_state.camera_group_configs is None:
                raise ValueError("No camera configurations detected!")

            if self.app_state.camera_group:  # if `connect/` called w/o configs, reset existing connection
                self.app_state.close_camera_group()

            self.app_state.create_camera_group(camera_configs=camera_configs)
            self.app_state.camera_group.start()
            logger.info("Camera group started")
        except Exception as e:
            logger.exception(f"Error creating camera group:  {e}")
            raise

    def _detect_available_cameras(self, strategy: CameraDetectionStrategies):
        try:
            self.app_state.set_available_cameras(get_available_cameras(strategy=strategy))
        except Exception as e:
            logger.exception(f"Error detecting available devices: {e}")
            raise

    def open_video_group(self, video_folder_path: str | Path):
        logger.info("Opening video group...")
        try:
            video_folder_path = Path(video_folder_path)

            video_configs = load_video_configs_from_folder(synchronized_video_folder_path=video_folder_path)
            self.app_state.create_video_group(video_configs=video_configs)
            self.app_state.video_group.start()
            logger.info("Video group started")
        except Exception as e:
            logger.exception(f"Error opening video group: {e}")
            raise

    def play_videos(self):
        logger.info("Playing videos...")
        self.app_state.play_videos()

    def pause_videos(self):
        logger.info("Pausing videos...")
        self.app_state.pause_videos()

    def stop_videos(self):
        logger.info("Stopping videos...")
        self.app_state.stop_videos()

    def seek_videos(self, frame_number: int):
        logger.info(f"Seeking videos to frame {frame_number}...")
        self.app_state.seek_videos(frame_number=frame_number)

    def update_video_configs(self, video_folder_path: str | Path):
        pass  # TODO: not sure if this is needed

    def close_camera_group(self):
        logger.info("Closing camera group...")
        self.app_state.close_camera_group()

    def close_video_group(self):
        logger.info("Closing video group...")
        self.app_state.close_video_group()

    def shutdown(self):
        logger.info("Closing controller...")
        self.app_state.ipc_flags.global_kill_flag.value = True
        if self.app_state.camera_group:
            self.close_camera_group()
        if self.app_state.video_group:
            self.app_state.close_video_group()


SKELLYCAM_APP_CONTROLLER = None


def create_skellycam_app_controller(global_kill_flag: multiprocessing.Value
                                    ) -> SkellycamAppController:
    global SKELLYCAM_APP_CONTROLLER
    if not SKELLYCAM_APP_CONTROLLER:
        SKELLYCAM_APP_CONTROLLER = SkellycamAppController.create(
            skellycam_app_state=create_skellycam_app_state(global_kill_flag=global_kill_flag))


    return SKELLYCAM_APP_CONTROLLER


def get_skellycam_app_controller() -> SkellycamAppController:
    global SKELLYCAM_APP_CONTROLLER
    if not isinstance(SKELLYCAM_APP_CONTROLLER, SkellycamAppController):
        raise ValueError("AppController not created!")
    return SKELLYCAM_APP_CONTROLLER
