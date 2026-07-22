from __future__ import annotations

import io
import logging
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

from PIL import Image
from rembg import new_session, remove

from app.config import settings
from app.utils.edge_cleanup import (
    apply_mask_keep_original_colors,
    pad_for_cutout,
    unpad_cutout,
)
from app.utils.image_utils import ensure_rgba
from app.utils.memory import free_memory, is_oom_error

logger = logging.getLogger(__name__)

StatusCallback = Callable[[str], None]


class BiRefNetService:
    """Local BG removal with automatic downscale-on-OOM (never hard-fails)."""

    def __init__(self) -> None:
        self._session = None
        self._loaded_model: str | None = None

    @property
    def model_name(self) -> str:
        return settings.birefnet_model

    def _model_path(self, name: str) -> Path:
        return Path.home() / ".u2net" / f"{name}.onnx"

    def model_cached(self, name: str | None = None) -> bool:
        path = self._model_path(name or self.model_name)
        return path.exists() and path.stat().st_size > 100_000

    def _build_session(self, model_name: str):
        logger.info("Loading rembg session (%s)…", model_name)
        try:
            return new_session(model_name, providers=["CPUExecutionProvider"])
        except TypeError:
            return new_session(model_name)

    def unload(self) -> None:
        self._session = None
        self._loaded_model = None
        free_memory("BiRefNet unload")

    def get_session(self, model_name: str | None = None):
        name = model_name or self.model_name
        if self._session is None or self._loaded_model != name:
            self.unload()
            self._session = self._build_session(name)
            self._loaded_model = name
        return self._session

    def warm_up(self) -> None:
        self.get_session(self.model_name)

    def _run_remove(self, work: Image.Image, session) -> Image.Image:
        cutout = remove(
            work,
            session=session,
            alpha_matting=False,
            only_mask=False,
            post_process_mask=True,
        )
        if not isinstance(cutout, Image.Image):
            cutout = Image.open(io.BytesIO(cutout))
        return ensure_rgba(cutout)

    def _finish(
        self,
        original: Image.Image,
        padded: Image.Image,
        pad: int,
        cutout: Image.Image,
        on_status: Optional[StatusCallback],
    ) -> Image.Image:
        if cutout.size != padded.size:
            if on_status:
                on_status("Restoring original colors & detail…")
            alpha = cutout.split()[-1].resize(padded.size, Image.Resampling.LANCZOS)
            mask_img = Image.new("RGBA", padded.size, (0, 0, 0, 0))
            mask_img.putalpha(alpha)
        else:
            mask_img = cutout
        result = apply_mask_keep_original_colors(padded, mask_img)
        result = unpad_cutout(result, pad)
        if settings.unload_models_after_use:
            self.unload()
        return result

    def remove_background(
        self,
        image: Image.Image,
        on_status: Optional[StatusCallback] = None,
    ) -> Image.Image:
        original = ensure_rgba(image)
        padded, pad = pad_for_cutout(original, pad=settings.birefnet_pad)
        fw, fh = padded.size

        # Prefer lite → tiny. Always end with u2netp at tiny size.
        models = [self.model_name]
        for extra in ("birefnet-general-lite", "u2netp"):
            if extra not in models:
                models.append(extra)

        side_steps = [
            settings.birefnet_max_side,
            640,
            512,
            384,
        ]
        # unique descending
        seen: set[int] = set()
        sides: list[int] = []
        for s in side_steps:
            s = int(s)
            if s not in seen and s >= 320:
                seen.add(s)
                sides.append(s)

        last_error: Exception | None = None

        for name in models:
            for side in sides:
                try:
                    if max(fw, fh) > side:
                        scale = side / float(max(fw, fh))
                        work = padded.resize(
                            (max(1, int(fw * scale)), max(1, int(fh * scale))),
                            Image.Resampling.BILINEAR,
                        )
                    else:
                        work = padded

                    if not self.model_cached(name):
                        if on_status:
                            on_status(f"Downloading {name} (one-time)…")
                    elif on_status:
                        on_status(f"Loading {name}…")

                    free_memory("before rembg")
                    session = self.get_session(name)
                    if on_status:
                        on_status(
                            f"Removing background on {work.size[0]}×{work.size[1]}…"
                        )

                    cutout = self._run_remove(work, session)
                    return self._finish(original, padded, pad, cutout, on_status)

                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    logger.warning("%s @ %spx failed: %s", name, side, exc)
                    self.unload()
                    free_memory("rembg retry")
                    if is_oom_error(exc):
                        if on_status:
                            on_status(f"Low RAM — auto-shrinking to {side}px…")
                        continue
                    # non-OOM: try next model
                    break

        # Absolute last resort: tiny u2netp — almost never OOMs
        try:
            if on_status:
                on_status("Safe mode — tiny model…")
            self.unload()
            free_memory("safe mode")
            work = padded.resize((512, 512), Image.Resampling.BILINEAR)
            session = self.get_session("u2netp")
            cutout = self._run_remove(work, session)
            return self._finish(original, padded, pad, cutout, on_status)
        except Exception as exc:  # noqa: BLE001
            self.unload()
            raise RuntimeError(
                "Background removal failed even in safe mode. "
                "Close Chrome/other apps and retry. "
                f"Detail: {last_error or exc}"
            ) from exc


@lru_cache(maxsize=1)
def get_birefnet_service() -> BiRefNetService:
    return BiRefNetService()
