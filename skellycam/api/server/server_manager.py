import logging
import multiprocessing
import threading
import time
from typing import Optional

import uvicorn
from uvicorn import Server

from skellycam.api.server.server_constants import HOSTNAME, PORT
from skellycam.skellycam_app.skellycam_app_controller.skellycam_app_controller import create_skellycam_app_controller
from skellycam.skellycam_app.skellycam_app_lifespan.create_skellycam_app import create_skellycam_app
from skellycam.skellycam_app.skellycam_process_manager.skellycam_process_manager import \
    create_skellycam_process_manager, get_skellycam_process_manager
from skellycam.utilities.kill_process_on_port import kill_process_on_port

logger = logging.getLogger(__name__)


class UvicornServerManager:
    def __init__(self,
                 global_kill_flag: multiprocessing.Value,
                 hostname: str = HOSTNAME,
                 port: int = PORT,
                 log_level: str = "info"):
        self._global_kill_flag = global_kill_flag
        create_skellycam_app_controller(global_kill_flag=global_kill_flag)
        self.hostname: str = hostname
        self.port: int = port
        self.server_thread: Optional[threading.Thread] = None
        self.server: Optional[Server] = None
        self.log_level: str = log_level

    @property
    def is_running(self):
        return self.server_thread.is_alive() if self.server_thread else False

    def run_server(self):

        config = uvicorn.Config(
            create_skellycam_app,
            host=self.hostname,
            port=self.port,
            log_level=0,  # self.log_level,
            reload=True,
            factory=True
        )

        logger.info(f"Starting uvicorn server on {self.hostname}:{self.port}")
        kill_process_on_port(port=self.port)
        self.server = uvicorn.Server(config)

        def server_thread():
            logger.debug("Server thread started")
            try:
                logger.debug("Running uvicorn server...")
                self.server.run()
                while not self._global_kill_flag.value:
                    logger.trace("Server heartbeat says 'beep'")
                    time.sleep(2)
            except Exception as e:
                logger.error(f"A fatal error occurred in the uvicorn server: {e}")
                logger.exception(e)
                raise
            finally:
                logger.info(f"Uvicorn server thread completed")

        self.server_thread = threading.Thread(target=server_thread)
        self.server_thread.start()
        self.server_thread.join()
        logger.debug("Server thread shutdown")

    def shutdown_server(self):
        logger.info("Shutting down Uvicorn Server...")
        self._global_kill_flag.value = True
        if self.server:
            self.server.should_exit = True
            waiting_time = 0
            while self.server_thread.is_alive():
                waiting_time += 1
                time.sleep(1)
                if waiting_time > 3:
                    logger.debug("Server thread is not shutting down. Forcing exit...")
                    self.server.force_exit = True
                if waiting_time > 5:
                    logger.debug("Server thread is not shutting down. Killing process...")
                    kill_process_on_port(port=self.port)

            logger.info("Uvicorn Server shutdown successfully")
