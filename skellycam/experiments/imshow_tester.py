import asyncio

from skellycam.backend.detection.detect_cameras import detect_cameras
from skellycam.backend.opencv import Camera
from skellycam.data_models.camera_config import CameraConfig


async def imshow_testing():
    cams = detect_cameras()
    cvcams = []
    for info in cams.cameras_found_list:
        c = Camera(CameraConfig(camera_id=info))
        c.connect()
        cvcams.append(c)

    await asyncio.gather(*[cam.show_async() for cam in cvcams])


if __name__ == "__main__":
    asyncio.run(imshow_testing())
