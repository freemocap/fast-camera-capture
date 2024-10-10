import logging

from pydantic import BaseModel, ConfigDict

from skellycam.app.app_controller.ipc_flags import IPCFlags
from skellycam.core.camera_group.camera.config.camera_config import CameraConfigs
from skellycam.core.camera_group.shmorchestrator.camera_group_orchestrator import CameraGroupOrchestrator
from skellycam.core.camera_group.shmorchestrator.camera_shared_memory_manager import CameraGroupSharedMemory, \
    CameraGroupSharedMemoryDTO

logger = logging.getLogger(__name__)


class CameraGroupSharedMemoryOrchestratorDTO(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    camera_group_shm_dto: CameraGroupSharedMemoryDTO
    camera_group_orchestrator: CameraGroupOrchestrator


class CameraGroupSharedMemoryOrchestrator(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    camera_group_shm: CameraGroupSharedMemory
    camera_group_orchestrator: CameraGroupOrchestrator

    @classmethod
    def create(cls,
               camera_configs: CameraConfigs,
               ipc_flags: IPCFlags,
               read_only: bool):

        return cls(camera_group_shm = CameraGroupSharedMemory.create(camera_configs=camera_configs,
                                                                     read_only=read_only),
                   camera_group_orchestrator=CameraGroupOrchestrator.create(camera_configs=camera_configs,
                                                                            ipc_flags=ipc_flags)
                   )

    @classmethod
    def recreate(cls,
                 dto: CameraGroupSharedMemoryOrchestratorDTO,
                 read_only: bool):
        return cls(
            camera_group_shm=CameraGroupSharedMemory.recreate(dto=dto.camera_group_shm_dto,
                                                              read_only=read_only),
            camera_group_orchestrator=dto.camera_group_orchestrator,
        )

    @property
    def valid(self):
        return self.camera_group_shm.shm_valid_flag.value

    def to_dto(self) -> CameraGroupSharedMemoryOrchestratorDTO:
        return CameraGroupSharedMemoryOrchestratorDTO(camera_group_shm_dto=self.camera_group_shm.to_dto(),
                                                      camera_group_orchestrator=self.camera_group_orchestrator)

    def close(self):
        logger.debug("Closing CameraGroupSharedMemoryOrchestrator...")
        self.camera_group_shm.close_and_unlink()
