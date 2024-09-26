import logging
import platform
from pprint import pprint
from typing import List, Tuple

import cv2
from PySide6.QtCore import QCoreApplication
from PySide6.QtMultimedia import QCameraDevice

from skellycam.api.app.app_state import get_app_state
from skellycam.core.detection.camera_device_info import CameraDeviceInfo

logger = logging.getLogger(__name__)


async def detect_available_devices(check_if_available: bool = False):
    from PySide6.QtMultimedia import QMediaDevices
    # TODO - deprecate `/camreas/detect/` route and move 'detection' responsibilities to client
    if not QCoreApplication.instance():
        app = QCoreApplication([])
    else:
        app = QCoreApplication.instance()
    logger.info("Detecting available cameras...")
    devices = QMediaDevices()
    detected_cameras = devices.videoInputs()

    if platform.system() == "Darwin":
        detected_cameras, camera_ports = await order_darwin_cameras(detected_cameras=detected_cameras)
    else:
        camera_ports = range(len(detected_cameras))

    camera_devices = {}
    for camera_number, camera in zip(camera_ports, detected_cameras):

        if check_if_available:
            await _check_camera_available(camera_number)

        camera_device_info = CameraDeviceInfo.from_q_camera_device(
            camera_number=camera_number, camera=camera
        )
        camera_devices[camera_device_info.cv2_port] = camera_device_info
    logger.debug(f"Detected camera_devices: {list(camera_devices.keys())}")
    get_app_state().available_devices = {camera_id: device for camera_id, device in camera_devices.items()}


async def _check_camera_available(port: int) -> bool:
    logger.debug(f"Checking if camera on port: {port} is available...")
    cap = cv2.VideoCapture(port)
    success, frame = cap.read()
    if not cap.isOpened() or not success or frame is None:
        logger.debug(f"Camera on port: {port} is not available...")
        return False
    logger.debug(f"Camera on port: {port} is available!")
    cap.release()
    return True

async def order_darwin_cameras(detected_cameras: List[QCameraDevice]) -> Tuple[List[QCameraDevice], List[int]]:
    """
    Reorder QMultiMediaDevices to match order of OpenCV ports on macOS. 

    Removes virtual cameras, and assumes virtual cameras are always last. 
    Also assumes that once virtual cameras are removed, the order of the cameras from Qt will match the order of OpenCV.
    """
    camera_ports = await detect_opencv_ports()
    for camera in detected_cameras:
        if "Virtual" in camera.description():
            detected_cameras.remove(camera)
            camera_ports.pop()  # assumes virtual camera is always last
    if len(camera_ports) != len(detected_cameras):
        raise ValueError(f"OpenCV and Qt did not detect same number of cameras: OpenCV: {len(camera_ports)} !=  Qt: {len(detected_cameras)}")

    return detected_cameras, camera_ports


async def detect_opencv_ports(max_ports: int = 20, max_unused_ports: int = 5) -> List[int]:
    unused = 0
    port = 0
    ports = []
    while port < max_ports and unused < max_unused_ports:
        camera_available = await _check_camera_available(port)
        if camera_available:
            ports.append(port)
        else:
            unused += 1
        port += 1

    return ports


if __name__ == "__main__":
    import asyncio
    cameras_out = asyncio.run(detect_available_devices())
    pprint(cameras_out, indent=4)
