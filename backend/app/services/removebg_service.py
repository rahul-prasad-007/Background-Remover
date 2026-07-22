from __future__ import annotations

import io
import logging
from functools import lru_cache
from typing import Callable, Optional

import httpx
from PIL import Image

from app.config import settings
from app.utils.edge_cleanup import apply_mask_keep_original_colors, pad_for_cutout, unpad_cutout
from app.utils.image_utils import ensure_rgba

logger = logging.getLogger(__name__)

StatusCallback = Callable[[str], None]

REMOVE_BG_URL = "https://api.remove.bg/v1.0/removebg"


class RemoveBgService:
    """Cloud background removal — returns original colors + API alpha mask."""

    def remove_background(
        self,
        image: Image.Image,
        on_status: Optional[StatusCallback] = None,
    ) -> Image.Image:
        api_key = (settings.remove_bg_api_key or "").strip()
        if not api_key:
            raise RuntimeError(
                "REMOVE_BG_API_KEY is missing. Add your remove.bg API key to backend/.env"
            )

        original = ensure_rgba(image)
        padded, pad = pad_for_cutout(original, pad=40)

        buf = io.BytesIO()
        padded.convert("RGB").save(buf, format="PNG", optimize=True)
        payload = buf.getvalue()

        if on_status:
            on_status("Uploading full-quality image to remove.bg…")

        headers = {"X-Api-Key": api_key}
        data = {
            "size": settings.remove_bg_size,
            "format": "png",
            "type": settings.remove_bg_type,
            "channels": "rgba",
        }
        files = {"image_file": ("upload.png", payload, "image/png")}

        try:
            with httpx.Client(timeout=settings.remove_bg_timeout) as client:
                if on_status:
                    on_status("remove.bg is cutting out the subject…")
                response = client.post(
                    REMOVE_BG_URL,
                    headers=headers,
                    data=data,
                    files=files,
                )
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                "remove.bg request timed out. Check your internet connection."
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"remove.bg network error: {exc}") from exc

        if response.status_code == 403:
            raise RuntimeError("remove.bg API key is invalid or expired.")
        if response.status_code == 402:
            raise RuntimeError("remove.bg credits exhausted. Top up your account.")
        if response.status_code == 429:
            raise RuntimeError("remove.bg rate limit hit. Wait a moment and retry.")
        if response.status_code >= 400:
            detail = response.text[:300]
            raise RuntimeError(f"remove.bg error ({response.status_code}): {detail}")

        if on_status:
            on_status("Restoring original colors & filling gaps…")

        api_cutout = Image.open(io.BytesIO(response.content))
        api_cutout.load()
        api_cutout = ensure_rgba(api_cutout)

        # Keep ORIGINAL photo colors — only use API for the mask
        result = apply_mask_keep_original_colors(padded, api_cutout)
        result = unpad_cutout(result, pad)

        logger.info("remove.bg done → %sx%s", result.width, result.height)
        return result


@lru_cache(maxsize=1)
def get_removebg_service() -> RemoveBgService:
    return RemoveBgService()
