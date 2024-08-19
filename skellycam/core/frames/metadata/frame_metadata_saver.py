from csv import DictWriter
from pathlib import Path
from typing import List, Optional, Any

from pydantic import BaseModel, Field

from skellycam.core import CameraId
from skellycam.core.frames.metadata.frame_metadata import FrameMetadata, FRAME_METADATA_MODEL
from skellycam.core.frames.payload_models.frame_payload import FramePayload


class FrameMetadataSaver(BaseModel):
    """
    Holds a list of FrameMetadata objects, one per frame of a recording
    """
    camera_id: CameraId
    frame_metadata_list: List[FrameMetadata] = Field(default_factory=list)

    file_handle: Optional[Any] = None
    csv_writer: Optional[DictWriter] = None

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def create(cls,
               frame_metadata: FrameMetadata,
               recording_name: str,
               save_path: str):
        cls._validate_input(frame_metadata, save_path)
        csv_file_name = f"{recording_name}_camera_{frame_metadata.camera_id}_timestamps.csv"
        full_csv_path = str(Path(save_path) / csv_file_name)
        file_handle = open(full_csv_path, mode="x", newline="")
        csv_writer = DictWriter(file_handle, fieldnames=[key.value for key in FRAME_METADATA_MODEL])
        csv_writer.writeheader()
        return cls(camera_id=frame_metadata.camera_id,
                   file_handle=file_handle,
                   csv_writer=csv_writer)

    @classmethod
    def _validate_input(cls, frame_metadata, save_path):
        if not Path(save_path).exists():
            raise ValueError(f"Save path {save_path} does not exist")

        if frame_metadata.frame_number != 0:
            raise ValueError(f"FrameMetadata frame_number {frame_metadata.frame_number} must be 0")

    def add_frame(self, frame: FramePayload):
        frame_metadata = FrameMetadata.from_array(metadata_array=frame.metadata)
        self._validate(frame_metadata)
        self.frame_metadata_list.append(frame_metadata)

    def _validate(self, frame_metadata: FrameMetadata):
        if frame_metadata.camera_id != self.camera_id:
            raise ValueError(
                f"FrameMetadata camera_id {frame_metadata.camera_id} does not match FrameMetadataList camera_id {self.camera_id}")
        if frame_metadata.frame_number != len(self.frame_metadata_list):
            raise ValueError(
                f"FrameMetadata frame_number {frame_metadata.frame_number} does not match FrameMetadataList length: {len(self.frame_metadata_list)}")

    def close(self):
        self.file_handle.close()

    def __len__(self):
        return len(self.frame_metadata_list)
