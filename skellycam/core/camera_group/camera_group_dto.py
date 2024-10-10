import multiprocessing
from dataclasses import dataclass

from skellycam.app.app_controller.ipc_flags import IPCFlags
from skellycam.core.camera_group.camera.config.camera_config import CameraConfigs
from skellycam.core.camera_group.shmorchestrator.camera_group_shmorchestrator import \
    CameraGroupSharedMemoryOrchestratorDTO


@dataclass
class CameraGroupDTO:
    camera_configs: CameraConfigs
    shmorc_dto: CameraGroupSharedMemoryOrchestratorDTO
    ipc_queue: multiprocessing.Queue
    config_update_queue = multiprocessing.Queue()  # Update camera configs

    ipc_flags: IPCFlags

    _lock = multiprocessing.Lock()

    @property
    def camera_ids(self):
        return list(self.camera_configs.keys())

    def update_camera_configs(self, camera_configs: CameraConfigs):
        with self._lock:
            self.camera_configs = camera_configs