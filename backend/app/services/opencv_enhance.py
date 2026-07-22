from __future__ import annotations

from functools import lru_cache

from PIL import Image

from app.utils.edge_cleanup import polish_for_zoom
from app.utils.image_utils import ensure_rgba


class OpenCVEnhanceService:
    """
    Final print polish for transparent cutouts.
    Smooth zoomed edges + clear interior features (no waxed/blurred subject).
    """

    def enhance(self, image: Image.Image) -> Image.Image:
        rgba = ensure_rgba(image)
        return polish_for_zoom(rgba)


@lru_cache(maxsize=1)
def get_opencv_enhance_service() -> OpenCVEnhanceService:
    return OpenCVEnhanceService()
