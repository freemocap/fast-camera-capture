import logging

LOG_FILE = "log\synchronizer.log"
LOG_LEVEL = logging.DEBUG
LOG_FORMAT = " %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"

logging.basicConfig(filename=LOG_FILE, filemode="w", format=LOG_FORMAT, level=LOG_LEVEL)

from skellycam.detection.models.frame_payload import FramePayload
import sys
import time
from pathlib import Path
from queue import Queue
from threading import Thread, Event

import cv2
import numpy as np


class Synchronizer:
    def __init__(self, ports):
        # self.streams = streams
        self.current_bundle = None

        self.stop_event = Event()
        self.ports = ports
        self.frame_data = {}

        self.port_frame_count = {port: 0 for port in self.ports}
        self.port_current_frame = {port: 0 for port in self.ports}
        self.mean_frame_times = []
        self.bundle_out_q = Queue()
        self.spin_up()
        
    def stop(self):
        self.stop_event.set()
        self.bundler.join()
        for t in self.threads:
            t.join()

    def spin_up(self):

        logging.info("Starting frame bundler...")
        self.bundler = Thread(target=self.bundle_frames, args=(), daemon=True)
        self.bundler.start()

    def add_frame_payload(self, payload: FramePayload):

        frame_index = self.port_frame_count[payload.camera_id]
        key = f"{payload.camera_id}_{frame_index}"
        self.frame_data[key] = {
            "port": payload.camera_id,
            "frame": payload.image,
            "frame_index": frame_index,
            "frame_time": payload.timestamp_ns,
        }
        self.port_frame_count[payload.camera_id] += 1

    def earliest_next_frame(self, port):
        """Looks at next unassigned frame across the ports to determine
        the earliest time at which each of them was read"""
        times_of_next_frames = []
        for p in self.ports:

            next_index = (
                self.port_current_frame[p] + 1
            )  # note that this is no longer true if skellycam drops a frame

            frame_data_key = f"{p}_{next_index}"

            # problem with outpacing the threads reading data in, so wait if need be
            while frame_data_key not in self.frame_data.keys():
                logging.debug(
                    f"Waiting in a loop for frame data to populate with key: {frame_data_key}"
                )
                time.sleep(0.001)

            next_frame_time = self.frame_data[frame_data_key]["frame_time"]
            if p != port:
                times_of_next_frames.append(next_frame_time)

        return min(times_of_next_frames)

    def latest_current_frame(self, port):
        """Provides the latest frame_time of the current frames not inclusive of the provided port"""
        times_of_current_frames = []
        for p in self.ports:
            current_index = self.port_current_frame[p]
            current_frame_time = self.frame_data[f"{p}_{current_index}"]["frame_time"]
            if p != port:
                times_of_current_frames.append(current_frame_time)

        return max(times_of_current_frames)

    def min_frame_slack(self):
        """Determine how many unassigned frames are sitting in self.dataframe"""

        slack = [
            self.port_frame_count[port] - self.port_current_frame[port]
            for port in self.ports
        ]
        # logging.debug(f"Min slack in frames is {min(slack)}")
        logging.debug(f"Slack in frames is {slack}")
        return min(slack)

    def max_frame_slack(self):
        """Determine how many unassigned frames are sitting in self.dataframe"""

        slack = [
            self.port_frame_count[port] - self.port_current_frame[port]
            for port in self.ports
        ]

        logging.debug(f"Max frame slack is {max(slack)}")

        return max(slack)


    def bundle_frames(self):

        logging.info("About to start bundling frames...")
        while not self.stop_event.is_set():

            # need to wait for data to populate before synchronization can begin
            while self.min_frame_slack() < 2:
                logging.debug("Waiting for all ports to fully populate")
                time.sleep(0.01)

            next_layer = {}
            layer_frame_times = []

            # build earliest next/latest current dictionaries for each port to determine where to put frames
            # must be done before going in and making any updates to the frame index
            earliest_next = {}
            latest_current = {}

            for port in self.ports:
                earliest_next[port] = self.earliest_next_frame(port)
                latest_current[port] = self.latest_current_frame(port)
                current_frame_index = self.port_current_frame[port]

            for port in self.ports:
                current_frame_index = self.port_current_frame[port]

                port_index_key = f"{port}_{current_frame_index}"
                current_frame_data = self.frame_data[port_index_key]
                frame_time = current_frame_data["frame_time"]

                # don't put a frame in a bundle if the next bundle has a frame before it
                if frame_time > earliest_next[port]:
                    # definitly should be put in the next layer and not this one
                    next_layer[port] = None
                    logging.warning(f"Skipped frame at port {port}: > earliest_next")
                elif (
                    earliest_next[port] - frame_time < frame_time - latest_current[port]
                ):  # frame time is closer to earliest next than latest current
                    # if it's closer to the earliest next frame than the latest current frame, bump it up
                    # only applying for 2 camera setup where I noticed this was an issue (frames stay out of synch)
                    next_layer[port] = None
                    logging.warning(
                        f"Skipped frame at port {port}: delta < time-latest_current"
                    )
                else:
                    # add the data and increment the index
                    next_layer[port] = self.frame_data.pop(port_index_key)
                    self.port_current_frame[port] += 1
                    layer_frame_times.append(frame_time)
                    logging.debug(
                        f"Adding to layer from port {port} at index {current_frame_index} and frame time: {frame_time}"
                    )

            logging.debug(f"Unassigned Frames: {len(self.frame_data)}")

            self.mean_frame_times.append(np.mean(layer_frame_times))

            self.current_bundle = next_layer
            self.bundle_out_q.put(self.current_bundle)

        logging.info("Frame bundler successfully ended")
