"""Top-level package for skellycam."""

__author__ = """Skelly FreeMoCap"""
__email__ = 'info@freemocap.org'
__version__ = '0.1.1'

import logging
import sys
from pathlib import Path
base_package_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(base_package_path)) #add parent directory to sys.path

from skellycam.opencv.camera.camera import Camera
from skellycam.opencv.camera.models.camera_config import CameraConfig
from skellycam.system.log_config.logsetup import configure_logging

logger = logging.getLogger(__name__)

configure_logging()
