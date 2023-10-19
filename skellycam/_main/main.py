import multiprocessing

from skellycam import logger
from skellycam.main.main_loop import main_loop


def main():
    logger.info(f"Starting main...")

    exit_event = multiprocessing.Event()

    main_loop(exit_event)  # This is where the magic happens 💀📸✨

    logger.info(f"Exiting main...")
