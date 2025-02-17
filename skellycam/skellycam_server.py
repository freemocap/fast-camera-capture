import logging
import multiprocessing
import time

from skellycam.api.server.server_manager import UvicornServerManager
from skellycam.api.server.server_singleton import create_server_manager

logger = logging.getLogger(__name__)


def run_server(global_kill_flag: multiprocessing.Value):
    server_manager:UvicornServerManager = create_server_manager(global_kill_flag=global_kill_flag)
    try:
        server_manager.run_server()
    except Exception as e:
        logger.error(f"Server main process ended with error: {e}")
        raise
    finally:
        global_kill_flag.value = True
        server_manager.shutdown_server()

    logger.info("Server main process ended")




if __name__ == "__main__":
    outer_global_kill_flag = multiprocessing.Value("b", False)
    run_server(outer_global_kill_flag)
    outer_global_kill_flag.value = True
    print("Done!")
