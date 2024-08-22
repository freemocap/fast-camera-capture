import asyncio
import logging
import multiprocessing
from typing import Optional, List, Dict

from pydantic import BaseModel

from skellycam.core.cameras.camera.config.camera_config import CameraConfigs, CameraConfig
from skellycam.core.detection.camera_device_info import AvailableDevices


class WebSocketStatus(BaseModel):
    connected: bool = False
    ping_interval_ns: Optional[int] = None


class ProcessStatus(BaseModel):
    process_name: str
    is_alive: bool
    pid: str
    parent_pid: str

    @classmethod
    def from_process(cls, process: multiprocessing.Process,
                     parent_pid: int):
        return cls(
            process_name=process.name,
            is_alive=process.is_alive(),
            pid=str(process.pid),
            parent_pid=str(parent_pid),
        )


class ApiCallLog(BaseModel):
    endpoint: str
    timestamp: float


logger = logging.getLogger(__name__)

class AppState:
    def __init__(self):
        self._camera_configs: Optional[CameraConfigs] = None
        self._available_devices: Optional[AvailableDevices] = None
        self._websocket_status: Optional[WebSocketStatus] = None
        self._record_frames_flag: Optional[multiprocessing.Value] = None
        self._kill_camera_group_flag: Optional[multiprocessing.Value] = None
        self._api_call_history: List[ApiCallLog] = []
        self._processes: Optional[Dict[str, ProcessStatus]] = None
        self._lock = multiprocessing.Lock()

        self._process_status_update_queue = multiprocessing.Queue()
        self._listener_task = asyncio.create_task(self._run_listener_loop())


    @property
    def camera_configs(self):
        with self._lock:
            return self._camera_configs

    @camera_configs.setter
    def camera_configs(self, value):
        with self._lock:
            self._camera_configs = value

    @property
    def available_devices(self):
        with self._lock:
            return self._available_devices

    @available_devices.setter
    def available_devices(self, value):
        with self._lock:
            self._available_devices = value
            if self._camera_configs is None:
                self._camera_configs = CameraConfigs()
                for camera_id in self._available_devices.keys():
                    self._camera_configs[camera_id] = CameraConfig(camera_id=camera_id)

    @property
    def websocket_status(self):
        with self._lock:
            return self._websocket_status

    @websocket_status.setter
    def websocket_status(self, value):
        with self._lock:
            self._websocket_status = value

    @property
    def record_frames_flag(self):
        if self._record_frames_flag is None:
            return False
        with self._lock:
            return self._record_frames_flag

    @record_frames_flag.setter
    def record_frames_flag(self, value: multiprocessing.Value):
        with self._lock:
            self._record_frames_flag = value

    @property
    def kill_camera_group_flag(self):
        if self._kill_camera_group_flag is None:
            return False
        with self._lock:
            return self._kill_camera_group_flag.value

    @kill_camera_group_flag.setter
    def kill_camera_group_flag(self, value: multiprocessing.Value):
        with self._lock:
            self._kill_camera_group_flag = value

    @property
    def api_call_history(self):
        with self._lock:
            return self._api_call_history

    @property
    async def processes(self):
        with self._lock:
            return self._processes

    async def log_api_call(self, api_call_log: ApiCallLog):
        with self._lock:
            self._api_call_history.append(api_call_log)

    async def add_process(self, process: multiprocessing.Process):
        with self._lock:
            self._processes[str(process.pid)] = ProcessStatus.from_process(process)

    async def remove_processes(self, process: multiprocessing.Process):
        with self._lock:
            self._processes.pop(str(process.pid))

    @property
    def process_status_update_queue(self):
        return self._process_status_update_queue

    def _run_listener_loop(self):
        logger.trace("Starting AppState listener loop...")
        while True:
            update_process_status: ProcessStatus = self._process_status_update_queue.get()
            if update_process_status is None:
                break
            logger.trace(f"Received update: {update_process_status}")
            with self._lock:
                if not update_process_status.is_alive:
                    self._processes.pop(update_process_status.pid)
                else:
                    self._processes[update_process_status.pid] = update_process_status

    def close(self):
        self._process_status_update_queue.put(None)
        self._listener_task.cancel()
        self._listener_task = None

APP_STATE = None

def get_app_state():
    global APP_STATE
    if APP_STATE is None:
        APP_STATE = AppState()
    return APP_STATE
