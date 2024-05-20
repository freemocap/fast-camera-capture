import time

import numpy as np

from skellycam.core import CameraId
from skellycam.core.frames.frame_payload import FramePayload


def test_create_frame(image_fixture: np.ndarray):
    # Arrange
    frame = FramePayload.create_empty(camera_id=CameraId(0),
                                      image_shape=image_fixture.shape,
                                      frame_number=0)
    frame.image = image_fixture
    frame.previous_frame_timestamp_ns = time.perf_counter_ns()
    frame.timestamp_ns = time.perf_counter_ns()
    frame.success = True
    assert frame.hydrated


def test_frame_payload_create_empty(image_fixture: np.ndarray):
    # Arrange
    frame = FramePayload.create_empty(camera_id=CameraId(0),
                                      image_shape=image_fixture.shape,
                                      frame_number=0)

    # Assert
    assert frame.camera_id == CameraId(0)
    assert frame.image_shape == image_fixture.shape
    assert frame.frame_number == 0
    assert frame.color_channels == 3
    assert not frame.hydrated


def test_frame_payload_create_hydrated_dummy(image_fixture: np.ndarray):
    # Arrange
    frame = FramePayload.create_hydrated_dummy(image=image_fixture)

    # Assert
    assert frame.camera_id == CameraId(0)
    assert frame.image_shape == image_fixture.shape
    assert frame.frame_number == 0
    assert frame.color_channels == 3
    assert frame.hydrated
    assert np.sum(frame.image - image_fixture) == 0


def test_frame_payload_create_unhydrated_dummy(image_fixture: np.ndarray):
    # Arrange
    frame = FramePayload.create_unhydrated_dummy(camera_id=CameraId(0),
                                                 image=image_fixture)

    # Assert
    assert frame.camera_id == CameraId(0)
    assert frame.image_shape == image_fixture.shape
    assert frame.frame_number == 0
    assert frame.color_channels == 3
    assert not frame.hydrated

    frame_buffer = frame.to_buffer(image=image_fixture)
    re_frame = frame.from_buffer(buffer=frame_buffer,
                                 image_shape=image_fixture.shape)

    assert frame.image_checksum == re_frame.image_checksum


def test_frame_from_previous(frame_payload_fixture):
    # Act
    frame = FramePayload.from_previous(previous=frame_payload_fixture)

    # Assert
    assert frame.camera_id == frame_payload_fixture.camera_id
    assert frame.image_shape == frame_payload_fixture.image_shape
    assert frame.frame_number == frame_payload_fixture.frame_number + 1
    assert frame.color_channels == frame_payload_fixture.color_channels
    assert not frame.hydrated


def test_frame_payload_to_and_from_buffer(frame_payload_fixture):
    # separate image from rest of frame payload, because that's how we put it into shm
    frame_wo_image = FramePayload(**frame_payload_fixture.dict(exclude={"image_data"}))
    assert not frame_wo_image.hydrated
    buffer = frame_wo_image.to_buffer(image=frame_payload_fixture.image)

    # Act
    recreated_frame = FramePayload.from_buffer(buffer=buffer,
                                               image_shape=frame_payload_fixture.image.shape)

    # Assert
    assert recreated_frame == frame_payload_fixture
    assert np.sum(recreated_frame.image - frame_payload_fixture.image) == 0


def test_frame_number_fixed_size(image_fixture: np.ndarray):
    # Arrange
    og_frame = FramePayload.create_empty(camera_id=CameraId(0),
                                      image_shape=image_fixture.shape,
                                      frame_number=0)

    og_frame_size = og_frame.to_buffer(image=image_fixture).nbytes

    for fr in range(int(1e5)):
        frame = FramePayload.create_empty(camera_id=CameraId(0),
                                          image_shape=image_fixture.shape,
                                          frame_number=fr)
        frame_size = frame.to_buffer(image=image_fixture).nbytes
        assert frame_size == og_frame_size