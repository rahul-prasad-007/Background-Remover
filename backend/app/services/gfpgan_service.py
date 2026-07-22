from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.config import settings
from app.utils.image_utils import ensure_rgba

logger = logging.getLogger(__name__)

GFPGAN_URL = (
    "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/"
    "GFPGANv1.4.pth"
)


class GFPGANService:
    """Face restoration with GFPGAN when the package is installed; safe fallback otherwise."""

    def __init__(self) -> None:
        self._restorer = None
        self._init_attempted = False

    def _ensure_weights(self) -> Path:
        weights = settings.weights_dir / "GFPGANv1.4.pth"
        if not weights.exists():
            logger.info("Downloading GFPGAN weights...")
            from torch.hub import download_url_to_file

            download_url_to_file(GFPGAN_URL, str(weights), progress=True)
        return weights

    def _get_restorer(self):
        if self._init_attempted:
            return self._restorer
        self._init_attempted = True

        if not settings.use_gfpgan_model:
            logger.info("Low-memory mode: using fast OpenCV face refine (skip GFPGAN weights)")
            self._restorer = None
            return None

        try:
            from gfpgan import GFPGANer

            model_path = self._ensure_weights()
            self._restorer = GFPGANer(
                model_path=str(model_path),
                upscale=settings.gfpgan_upscale,
                arch="clean",
                channel_multiplier=2,
                bg_upsampler=None,
                device=settings.device,
            )
            return self._restorer
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Official GFPGAN package unavailable (%s). "
                "Using print-safe OpenCV face refinement fallback.",
                exc,
            )
            self._restorer = None
            return None

    def _opencv_face_refine(self, image: Image.Image) -> Image.Image:
        """Mild face-region denoise + detail restore when GFPGAN package is missing."""
        from app.services.face_detection import get_face_detection_service

        rgba = ensure_rgba(image)
        alpha = np.array(rgba.split()[-1])
        bgr = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)
        faces = get_face_detection_service().detect(image)
        result = bgr.copy()
        for face in faces:
            x0, y0 = face.x, face.y
            x1, y1 = face.x + face.width, face.y + face.height
            roi = result[y0:y1, x0:x1]
            if roi.size == 0:
                continue
            refined = cv2.bilateralFilter(roi, d=5, sigmaColor=40, sigmaSpace=40)
            blur = cv2.GaussianBlur(refined, (0, 0), 1.0)
            refined = cv2.addWeighted(refined, 1.2, blur, -0.2, 0)
            result[y0:y1, x0:x1] = refined

        rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        out = np.dstack([rgb, alpha])
        return Image.fromarray(out, mode="RGBA")

    def restore(self, image: Image.Image) -> Image.Image:
        rgba = ensure_rgba(image)
        alpha = np.array(rgba.split()[-1])
        restorer = self._get_restorer()

        if restorer is None:
            return self._opencv_face_refine(rgba)

        bgr = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)
        try:
            _cropped, _faces, restored = restorer.enhance(
                bgr,
                has_aligned=False,
                only_center_face=False,
                paste_back=True,
                weight=0.5,
            )
            rgb = cv2.cvtColor(restored, cv2.COLOR_BGR2RGB)
            if rgb.shape[:2] != alpha.shape[:2]:
                alpha = cv2.resize(
                    alpha, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_CUBIC
                )
            return Image.fromarray(np.dstack([rgb, alpha]), mode="RGBA")
        except Exception as exc:  # noqa: BLE001
            logger.warning("GFPGAN enhance failed: %s", exc)
            return self._opencv_face_refine(rgba)


@lru_cache(maxsize=1)
def get_gfpgan_service() -> GFPGANService:
    return GFPGANService()
