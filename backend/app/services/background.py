from __future__ import annotations

import logging
from functools import lru_cache
from typing import Callable, Optional

from PIL import Image

from app.config import settings
from app.utils.edge_cleanup import decontaminate_edges

logger = logging.getLogger(__name__)

StatusCallback = Callable[[str], None]


class BackgroundService:
    """
    Unified background removal:
      - local  → rembg (unlimited) + original-color composite
      - removebg → remove.bg API + original-color composite
    """

    def remove_background(
        self,
        image: Image.Image,
        on_status: Optional[StatusCallback] = None,
    ) -> Image.Image:
        provider = (settings.bg_provider or "local").strip().lower()

        if provider == "removebg":
            if on_status:
                on_status("Using remove.bg cloud API…")
            from app.services.removebg_service import get_removebg_service

            cutout = get_removebg_service().remove_background(image, on_status=on_status)
        else:
            if on_status:
                on_status("Using local BiRefNet (unlimited)…")
            from app.services.birefnet import get_birefnet_service

            cutout = get_birefnet_service().remove_background(image, on_status=on_status)

        if on_status:
            on_status("Clearing white gaps → transparent…")
        # Gentle fringe + force white in-between gaps to transparency
        return decontaminate_edges(cutout, erode_px=1)


@lru_cache(maxsize=1)
def get_background_service() -> BackgroundService:
    return BackgroundService()
