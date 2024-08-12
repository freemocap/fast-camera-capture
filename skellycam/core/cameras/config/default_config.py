from enum import Enum

from skellycam.core import CameraId
from skellycam.core.detection.image_resolution import ImageResolution
from skellycam.core.detection.image_rotation_types import RotationTypes

DEFAULT_EXPOSURE = 0  # The -7 was breaking my integrated webcam, and there's no easy way to change this on the swaggerui

DEFAULT_IMAGE_HEIGHT: int = 1080
DEFAULT_IMAGE_WIDTH: int = 1920
DEFAULT_IMAGE_CHANNELS: int = 3
DEFAULT_FRAME_RATE: float = 30.0
DEFAULT_IMAGE_SHAPE: tuple = (DEFAULT_IMAGE_HEIGHT, DEFAULT_IMAGE_WIDTH, DEFAULT_IMAGE_CHANNELS)
DEFAULT_CAMERA_ID: CameraId = CameraId(0)
DEFAULT_RESOLUTION: ImageResolution = ImageResolution(height=DEFAULT_IMAGE_HEIGHT, width=DEFAULT_IMAGE_WIDTH)


class DefaultCameraConfig(Enum):
    CAMERA_ID = DEFAULT_CAMERA_ID
    USE_THIS_CAMERA = True
    RESOLUTION = DEFAULT_RESOLUTION
    COLOR_CHANNELS: int = DEFAULT_IMAGE_CHANNELS
    EXPOSURE: int = DEFAULT_EXPOSURE
    FRAMERATE: float = DEFAULT_FRAME_RATE
    ROTATION: RotationTypes = RotationTypes.NO_ROTATION
    CAPTURE_FOURCC: str = "MJPG"  # TODO - consider other capture codecs
    WRITER_FOURCC: str = "mp4v"  # TODO - consider other writer codecs
