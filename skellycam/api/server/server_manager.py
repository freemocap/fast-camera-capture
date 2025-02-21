import logging
import multiprocessing
import os
import threading
import time
from typing import Optional

import psutil
import uvicorn
from uvicorn import Server

from skellycam.api.server.server_constants import HOSTNAME, PORT
from skellycam.skellycam_app.skellycam_app_controller.skellycam_app_controller import create_skellycam_app_controller
from skellycam.skellycam_app.skellycam_app_lifespan.create_skellycam_app import create_skellycam_app
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
        self.server_thread: threading.Thread|None = None
        self.server: Server|None = None
        self.log_level: str = log_level
        self.shutdown_listener_thread = threading.Thread(target=self.shutdown_listener_loop,
                                                         name="UvicornServerManagerShutdownListenerThread",
                                                         daemon=True)
        self.shutdown_listener_thread.start()


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
                self.server.run() #blocks until server is stopped
            except Exception as e:
                logger.error(f"A fatal error occurred in the uvicorn server: {e}")
                logger.exception(e)
                raise
            finally:
                logger.info(f"Uvicorn server thread completed")

        self.server_thread = threading.Thread(target=server_thread, name="UvicornServerManagerThread", daemon=True)
        self.server_thread.start()
        while not self._global_kill_flag.value and self.server_thread.is_alive():
            time.sleep(1)
        logger.debug("Server thread shutdown")
        # kill_process_on_port(port=self.port)

    def shutdown_server(self):
        logger.info("Shutting down Uvicorn Server...")
        self._global_kill_flag.value = True
        if self.server:
            self.server.should_exit = True
        time.sleep(1)
        # Kill child processes
        current_process = psutil.Process()
        for child in current_process.children(recursive=True):
            logger.debug(f"Killing child process: {child}")
            child.kill()

    def shutdown_listener_loop(self):
        while self._global_kill_flag.value is False and not os.getenv("SKELLYCAM_SHOULD_SHUTDOWN"):
            time.sleep(1)
            if os.getenv("SKELLYCAM_SHOULD_SHUTDOWN"):
                logger.info("Detected SKELLYCAM_APP_SHUTDOWN environment variable - shutting down server")
                self.shutdown_server()
                break
            if self._global_kill_flag.value:
                logger.info("Detected global kill flag - shutting down server")
                self.shutdown_server()
                break
