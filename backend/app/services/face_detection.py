from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

import cv2
from PIL import Image

from app.config import settings
from app.utils.image_utils import pil_to_cv

YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)


@dataclass
class FaceBox:
    x: int
    y: int
    width: int
    height: int
    confidence: float

    @property
    def as_xyxy(self) -> Tuple[int, int, int, int]:
        return self.x, self.y, self.x + self.width, self.y + self.height


class FaceDetectionService:
    """Detect faces with OpenCV YuNet (FaceDetectorYN)."""

    def __init__(self) -> None:
        self._detector = None

    def _ensure_model(self) -> Path:
        path = settings.weights_dir / "face_detection_yunet_2023mar.onnx"
        if not path.exists():
            from torch.hub import download_url_to_file

            download_url_to_file(YUNET_URL, str(path), progress=True)
        return path

    def _get_detector(self, width: int, height: int):
        model_path = str(self._ensure_model())
        detector = cv2.FaceDetectorYN.create(
            model_path,
            "",
            (width, height),
            score_threshold=0.6,
            nms_threshold=0.3,
            top_k=5000,
        )
        return detector

    def detect(self, image: Image.Image) -> List[FaceBox]:
        """Return detected face boxes. Empty list means GFPGAN should be skipped."""
        cv_img = pil_to_cv(image)
        if cv_img.shape[2] == 4:
            bgr = cv_img[:, :, :3]
        else:
            bgr = cv_img

        h, w = bgr.shape[:2]
        detector = self._get_detector(w, h)
        detector.setInputSize((w, h))
        _retval, faces = detector.detect(bgr)

        results: List[FaceBox] = []
        if faces is None:
            return results

        for face in faces:
            x, y, fw, fh = face[:4].astype(int)
            score = float(face[-1])
            pad_x = int(fw * 0.15)
            pad_y = int(fh * 0.15)
            x0 = max(0, x - pad_x)
            y0 = max(0, y - pad_y)
            x1 = min(w, x + fw + pad_x)
            y1 = min(h, y + fh + pad_y)
            results.append(
                FaceBox(
                    x=x0,
                    y=y0,
                    width=x1 - x0,
                    height=y1 - y0,
                    confidence=score,
                )
            )
        return results

    def has_faces(self, image: Image.Image) -> bool:
        return len(self.detect(image)) > 0


@lru_cache(maxsize=1)
def get_face_detection_service() -> FaceDetectionService:
    return FaceDetectionService()
