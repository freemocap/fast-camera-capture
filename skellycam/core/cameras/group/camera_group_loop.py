import logging
import multiprocessing
import time
from typing import Optional, List

import numpy as np

from skellycam.core.cameras.camera.camera_manager import CameraManager
from skellycam.core.cameras.config.camera_config import CameraConfigs
from skellycam.core.cameras.group.camera_group_orchestrator import CameraGroupOrchestrator
from skellycam.core.memory.camera_shared_memory import GroupSharedMemoryNames
from skellycam.utilities.wait_functions import wait_10ms

logger = logging.getLogger(__name__)


def camera_group_trigger_loop(
        camera_configs: CameraConfigs,
        group_orchestrator: CameraGroupOrchestrator,
        group_shm_names: GroupSharedMemoryNames,
        exit_event: multiprocessing.Event,
        number_of_frames: Optional[int] = None,
):
    camera_manager = CameraManager(camera_configs=camera_configs,
                                   shared_memory_names=group_shm_names,
                                   group_orchestrator=group_orchestrator,
                                   exit_event=exit_event,
                                   )
    camera_manager.start_cameras()

    group_orchestrator.fire_initial_triggers()

    loop_count = 0
    elapsed_per_loop_ns = []
    try:
        logger.debug(f"Starting camera trigger loop for cameras: {list(camera_configs.keys())}...")
        while not exit_event.is_set():
            tik = time.perf_counter_ns()

            group_orchestrator.trigger_multi_frame_read()

            if number_of_frames is not None:
                check_loop_count(number_of_frames, loop_count, exit_event)

            if loop_count > 0:
                elapsed_per_loop_ns.append((time.perf_counter_ns() - tik))
            loop_count += 1

        logger.debug(f"Multi-camera trigger loop for cameras: {camera_manager.camera_ids}  ended")
        wait_10ms()
        log_time_stats(
            camera_configs=camera_configs,
            elapsed_per_loop_ns=elapsed_per_loop_ns,
        )
    finally:
        camera_manager.stop_cameras()
        group_orchestrator.clear_triggers()
        logger.debug(f"Multi-camera trigger loop for cameras: {camera_manager.camera_ids}  exited")


def log_time_stats(camera_configs: CameraConfigs,
                   elapsed_per_loop_ns: List[int]):
    number_of_cameras = len(camera_configs)
    resolution = str(camera_configs[0].resolution)
    number_of_frames = len(elapsed_per_loop_ns) + 1
    ideal_frame_rate = min([camera_config.framerate for camera_config in camera_configs.values()])

    logger.info(
        f"Read {number_of_frames} x {resolution} images read from {number_of_cameras} camera(s):"
        f"\n\tMEASURED FRAME RATE (ideal: {ideal_frame_rate} fps): "
        f"\n\t\tmean   : {(1e9 / np.mean(elapsed_per_loop_ns)):.2f} fps "
        f"\n\t\tmedian : {(1e9 / np.median(elapsed_per_loop_ns)):.2f} fps \n"
        f"\n\tTime elapsed per multi-frame loop  (ideal: {(ideal_frame_rate ** -1) * 1e3:.2f} ms) -  "
        f"\n\t\tmean(std)   : {np.mean(elapsed_per_loop_ns) / 1e6:.2f} ({np.std(elapsed_per_loop_ns) / 1e6:.2f}) ms"
        f"\n\t\tmedian(mad) : {np.median(elapsed_per_loop_ns) / 1e6:.2f} ({np.median(np.abs(elapsed_per_loop_ns - np.median(elapsed_per_loop_ns))) / 1e6:.2f}) ms"
    )


def check_loop_count(number_of_frames: int, loop_count: int, exit_event: multiprocessing.Event):
    if number_of_frames is not None:
        if loop_count + 1 >= number_of_frames:
            logger.trace(f"Reached number of frames: {number_of_frames} - setting `exit` event")
            exit_event.set()
