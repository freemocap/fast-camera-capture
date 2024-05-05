import asyncio
import logging
import multiprocessing
from multiprocessing import Process
from typing import Dict

from skellycam.backend.core.cameras.config.camera_config import CameraConfigs
from skellycam.backend.core.cameras.trigger_camera.trigger_camera import TriggerCamera
from skellycam.backend.core.device_detection.camera_id import CameraId
from skellycam.backend.core.frames.frame_payload import FramePayload
from skellycam.backend.core.frames.frontend_image_payload import FrontendImagePayload
from skellycam.backend.core.frames.multi_frame_payload import MultiFramePayload

logger = logging.getLogger(__name__)


async def trigger_camera_factory(config) -> TriggerCamera:
    camera = TriggerCamera()
    await camera.start(config)
    return camera


async def start_cameras(camera_configs: CameraConfigs) -> Dict[CameraId, TriggerCamera]:
    logger.info(f"Starting cameras: {list(camera_configs.keys())}")
    tasks = {camera_id: trigger_camera_factory(config) for camera_id, config in camera_configs.items()}
    results = await asyncio.gather(*tasks.values())
    cameras = dict(zip(tasks.keys(), results))
    for camera_id, camera in cameras.items():
        if not camera.is_connected:
            raise Exception(f"Failed to connect to camera {camera_id}")
    logger.success(f"All cameras connected: {list(cameras.keys())}")
    return cameras


async def trigger_camera_read(cameras: Dict[CameraId, TriggerCamera],
                              payload: MultiFramePayload) -> MultiFramePayload:
    logger.loop("Triggering camera read...")
    tasks = [camera.get_frame() for camera in cameras.values()]
    frames = await asyncio.gather(*tasks)
    logger.loop(f"Received: {len(frames)} frames from cameras {[frame.camera_id for frame in frames]}")
    for camera_id, frame in zip(cameras.keys(), frames):
        if frame is None:
            continue
        if not isinstance(frame, FramePayload):
            logger.error(f"Received unexpected frame type: {type(frame)}")
            continue
        payload[CameraId(camera_id)] = frame
    logger.loop(f"Trigger returned payload with frames from Cameras {list(payload.camera_ids)}")
    return payload


async def communication_queue_loop(cameras: Dict[CameraId, TriggerCamera],
                                   communication_queue: multiprocessing.Queue,
                                   exit_event: asyncio.Event):
    logger.debug("Starting communication queue loop")
    while not exit_event.is_set():
        if not communication_queue.empty():
            message = communication_queue.get()
            if message is None:
                logger.debug("Received `None` - setting `exit` event")
                exit_event.set()
                close_tasks = [camera.close() for camera in cameras.values()]
                await asyncio.gather(*close_tasks)
            elif isinstance(message, CameraConfigs):
                logger.debug("Updating camera configs")
                await update_camera_configs(cameras, message)
    logger.debug("Communication queue loop complete")


async def camera_trigger_loop(camera_configs: CameraConfigs,
                              frame_pipe,  # send-only pipe connection
                              communication_queue: multiprocessing.Queue,
                              exit_event: asyncio.Event):
    cameras = await start_cameras(camera_configs)
    # communication_queue_task = asyncio.create_task(communication_queue_loop(cameras, communication_queue, exit_event))
    print('hi')

    logger.info(f"Camera trigger loop started!")
    payload = MultiFramePayload.create(list(cameras.keys()))
    while not exit_event.is_set():
        payload = await trigger_camera_read(cameras, payload)
        payload = send_payload_down_pipe(frame_pipe, payload)

    # if not communication_queue_task.done():
    #     communication_queue.put(None)
    #     await communication_queue_task
    logger.debug("Camera trigger loop complete")


def send_payload_down_pipe(frame_pipe,  # send-only pipe connection
                           payload: MultiFramePayload) -> MultiFramePayload:
    logger.loop(f"Sending payload with {len(payload)} frames down pipe...")
    payload.add_log("before_putting_in_pipe_from_trigger_loop")
    frame_pipe.send_bytes(b"whee")
    logger.loop(f"Payload sent down pipe - creating next payload...")
    next_payload = MultiFramePayload.from_previous(payload)
    logger.loop(f"Next payload created with  - looping...")
    return next_payload


async def update_camera_configs(cameras: [CameraId, TriggerCamera], configs: CameraConfigs):
    tasks = []
    for camera, config in zip(cameras.values(), configs.values()):
        tasks.append(camera.update_config(config))
    await asyncio.gather(*tasks)


class CameraTriggerProcess:
    def __init__(
            self,
            camera_configs: CameraConfigs,
            frame_pipe,  # send-only pipe connection
    ):
        self._camera_configs = camera_configs
        self._communication_queue = multiprocessing.Queue()
        self._process = Process(
            name="CameraTriggerProcess",
            target=CameraTriggerProcess._run_process,
            args=(self._camera_configs,
                  frame_pipe,
                  self._communication_queue,
                  )
        )

    @property
    def camera_ids(self) -> [CameraId]:
        return list(self._camera_configs.keys())

    def start(self):
        logger.debug("Stating CameraTriggerProcess...")
        self._process.start()

    def update_configs(self, camera_configs: CameraConfigs):
        self._camera_configs = camera_configs
        self._communication_queue.put(camera_configs)

    async def close(self):
        logger.debug("Closing CameraTriggerProcess...")
        self._communication_queue.put(None)
        self._process.join()
        logger.debug("CameraTriggerProcess closed")

    @staticmethod
    def _run_process(camera_configs: CameraConfigs,
                     frame_pipe,  # send-only pipe connection
                     communication_queue: multiprocessing.Queue):
        logger.debug(f"CameraTriggerProcess started")
        exit_event = asyncio.Event()
        try:
            asyncio.run(camera_trigger_loop(camera_configs, frame_pipe, communication_queue, exit_event))
        except Exception as e:
            logger.error(f"Erorr in CameraTriggerProcess: {type(e).__name__} - {e}")
            raise
        logger.debug(f"CameraTriggerProcess complete")
