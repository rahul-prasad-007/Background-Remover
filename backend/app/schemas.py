from __future__ import annotations

from enum import Enum
from typing import Callable, Optional

from pydantic import BaseModel


class PipelineStage(str, Enum):
    UPLOADING = "uploading"
    REMOVING_BACKGROUND = "removing_background"
    DETECTING_FACES = "detecting_faces"
    RESTORING_FACES = "restoring_faces"
    ENHANCING_IMAGE = "enhancing_image"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    ERROR = "error"


STAGE_LABELS: dict[PipelineStage, str] = {
    PipelineStage.UPLOADING: "Uploading...",
    PipelineStage.REMOVING_BACKGROUND: "Removing Background...",
    PipelineStage.DETECTING_FACES: "Detecting Faces...",
    PipelineStage.RESTORING_FACES: "Restoring Faces...",
    PipelineStage.ENHANCING_IMAGE: "Enhancing Image...",
    PipelineStage.FINALIZING: "Finalizing...",
    PipelineStage.COMPLETE: "Complete",
    PipelineStage.ERROR: "Error",
}


class ProgressEvent(BaseModel):
    stage: PipelineStage
    label: str
    status: str  # pending | active | done | skipped | error
    progress: float  # 0-100 overall
    message: Optional[str] = None
    faces_found: Optional[int] = None
    download_url: Optional[str] = None
    job_id: Optional[str] = None


ProgressCallback = Callable[[ProgressEvent], None]
