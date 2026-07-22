from __future__ import annotations

import logging
from functools import lru_cache
from typing import Callable, Optional

import cv2
import numpy as np
from PIL import Image

from app.config import settings
from app.utils.image_utils import ensure_rgba
from app.utils.memory import free_memory

logger = logging.getLogger(__name__)

StatusCallback = Callable[[str], None]

REALESRGAN_X2_URL = (
    "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/"
    "RealESRGAN_x2plus.pth"
)


class RealESRGANService:
    """
    Real-ESRGAN upscaling (tiled, CPU-friendly).

    ×2  → one Real-ESRGAN pass (same as before — already fast enough)
    ×4  → FAST path: one Real-ESRGAN ×2 + Lanczos ×2
          (true double-ESRGAN / native ×4 is too slow on 8GB CPU PCs)
    """

    def __init__(self) -> None:
        self._model = None
        self._device = None

    def unload(self) -> None:
        self._model = None
        free_memory("Real-ESRGAN unload")

    def _ensure_weights(self):
        from torch.hub import download_url_to_file

        path = settings.weights_dir / "RealESRGAN_x2plus.pth"
        if not path.exists():
            logger.info("Downloading Real-ESRGAN x2 weights…")
            download_url_to_file(REALESRGAN_X2_URL, str(path), progress=True)
        return path

    def _get_model(self):
        import torch

        from app.services.rrdbnet import RRDBNet

        if self._model is not None:
            return self._model

        # Keep CPU thread count modest — oversubscription slows tiling
        torch.set_num_threads(max(1, min(4, settings.realesrgan_threads)))

        device = torch.device(settings.device)
        self._device = device
        model = RRDBNet(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_block=23,
            num_grow_ch=32,
            scale=2,
        )
        weights = self._ensure_weights()
        loadnet = torch.load(str(weights), map_location=device, weights_only=False)
        key = "params_ema" if "params_ema" in loadnet else "params"
        model.load_state_dict(loadnet[key], strict=True)
        model.eval().to(device)
        self._model = model
        logger.info("Real-ESRGAN x2 loaded on %s", device)
        return model

    def _shrink_for_speed(self, rgb: np.ndarray, alpha: np.ndarray, max_side: int):
        h, w = rgb.shape[:2]
        if max(h, w) <= max_side:
            return rgb, alpha
        scale = max_side / float(max(h, w))
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        logger.info("4× speed pre-shrink %sx%s → %sx%s", w, h, nw, nh)
        rgb_s = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA)
        alpha_s = cv2.resize(alpha, (nw, nh), interpolation=cv2.INTER_AREA)
        return rgb_s, alpha_s

    def _tile_enhance(
        self,
        rgb: np.ndarray,
        on_status: Optional[StatusCallback] = None,
    ) -> np.ndarray:
        import torch

        model = self._get_model()
        device = self._device
        h, w = rgb.shape[:2]
        tile = settings.realesrgan_tile
        pad = 6
        net_scale = 2
        output = np.zeros((h * net_scale, w * net_scale, 3), dtype=np.uint8)

        tiles_y = (h + tile - 1) // tile
        tiles_x = (w + tile - 1) // tile
        total = max(1, tiles_x * tiles_y)
        done = 0

        with torch.inference_mode():
            for y0 in range(0, h, tile):
                for x0 in range(0, w, tile):
                    x1, y1 = min(x0 + tile, w), min(y0 + tile, h)
                    xs0, ys0 = max(x0 - pad, 0), max(y0 - pad, 0)
                    xs1, ys1 = min(x1 + pad, w), min(y1 + pad, h)
                    tile_img = rgb[ys0:ys1, xs0:xs1]
                    tensor = (
                        torch.from_numpy(np.ascontiguousarray(tile_img))
                        .float()
                        .permute(2, 0, 1)
                        .unsqueeze(0)
                        .to(device)
                        / 255.0
                    )
                    out = model(tensor).float().clamp_(0, 1)
                    out_np = (
                        out.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255.0
                    ).round().astype(np.uint8)
                    top = (y0 - ys0) * net_scale
                    left = (x0 - xs0) * net_scale
                    bottom = top + (y1 - y0) * net_scale
                    right = left + (x1 - x0) * net_scale
                    output[
                        y0 * net_scale : y1 * net_scale,
                        x0 * net_scale : x1 * net_scale,
                    ] = out_np[top:bottom, left:right]
                    del tensor, out
                    done += 1
                    if on_status and done % max(1, total // 5) == 0:
                        on_status(f"Real-ESRGAN tiling… {int(100 * done / total)}%")

        return output

    def _cap_output(self, image: Image.Image) -> Image.Image:
        w, h = image.size
        max_side = settings.max_output_side
        if max(w, h) <= max_side:
            return image
        s = max_side / float(max(w, h))
        target = (max(1, int(w * s)), max(1, int(h * s)))
        logger.info("Capping output to %sx%s", *target)
        return image.resize(target, Image.Resampling.LANCZOS)

    def _pack(self, rgb: np.ndarray, alpha: np.ndarray) -> Image.Image:
        if alpha.shape[:2] != rgb.shape[:2]:
            alpha = cv2.resize(
                alpha, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_CUBIC
            )
        out = rgb.copy()
        out[alpha < 2] = 0
        return Image.fromarray(np.dstack([out, alpha]), mode="RGBA")

    def upscale(
        self,
        image: Image.Image,
        scale: int | None = None,
        on_status: Optional[StatusCallback] = None,
    ) -> Image.Image:
        from app.utils.memory import free_memory

        scale = int(scale or settings.realesrgan_scale)
        if scale not in (2, 4):
            scale = 2 if scale < 4 else 4

        rgba = ensure_rgba(image)
        w0, h0 = rgba.size

        # Progressive max sides — shrink automatically on OOM
        if scale == 4:
            candidates = [
                settings.realesrgan_4x_max_input,
                640,
                512,
                400,
            ]
        else:
            candidates = [
                min(settings.realesrgan_2x_max_input, settings.max_process_side),
                800,
                640,
                512,
            ]

        last_error: Exception | None = None
        for max_side in candidates:
            alpha = np.array(rgba.split()[-1])
            rgb = np.array(rgba.convert("RGB"))
            # Fill transparent with edge colors (not white) so upscale doesn't bake white speckles
            solid = (alpha >= 200).astype(np.uint8) * 255
            if cv2.countNonZero(solid) > 0:
                k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
                dil = cv2.dilate(solid, k, iterations=2)
                mask_f = (dil > 0).astype(np.float32)
                den = cv2.blur(mask_f, (9, 9)) + 1e-5
                filled = rgb.copy().astype(np.float32)
                for c in range(3):
                    filled[:, :, c] = cv2.blur(
                        rgb[:, :, c].astype(np.float32) * mask_f, (9, 9)
                    ) / den
                rgb = rgb.copy()
                low = alpha < 8
                rgb[low] = np.clip(filled, 0, 255).astype(np.uint8)[low]
            else:
                rgb = rgb.copy()
                rgb[alpha < 8] = 0
            try:
                free_memory("before esrgan")
                if scale == 4 and settings.realesrgan_fast_4x:
                    if on_status:
                        on_status(f"Fast ×4 @ {max_side}px…")
                    rgb, alpha = self._shrink_for_speed(rgb, alpha, max_side)
                    up2 = self._tile_enhance(rgb, on_status=on_status)
                    up4 = cv2.resize(
                        up2,
                        (up2.shape[1] * 2, up2.shape[0] * 2),
                        interpolation=cv2.INTER_LANCZOS4,
                    )
                    alpha_up = cv2.resize(
                        alpha,
                        (up4.shape[1], up4.shape[0]),
                        interpolation=cv2.INTER_CUBIC,
                    )
                    result = self._pack(up4, alpha_up)
                else:
                    if on_status:
                        on_status(f"Real-ESRGAN ×{scale} @ {max_side}px…")
                    rgb, alpha = self._shrink_for_speed(rgb, alpha, max_side)
                    up = self._tile_enhance(rgb, on_status=on_status)
                    if scale == 4:
                        up = self._tile_enhance(up, on_status=on_status)
                    result = self._pack(up, alpha)

                result = self._cap_output(result)
                if settings.unload_models_after_use:
                    self.unload()
                logger.info(
                    "Upscale ×%s done: %sx%s → %sx%s",
                    scale,
                    w0,
                    h0,
                    result.width,
                    result.height,
                )
                return result
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("ESRGAN @ max_side=%s failed: %s", max_side, exc)
                self.unload()
                free_memory("esrgan retry")
                if on_status:
                    on_status("Low RAM — retrying smaller upscale…")
                continue

        # Never fail the job — Lanczos always works
        logger.warning("ESRGAN exhausted retries (%s) — Lanczos fallback", last_error)
        if on_status:
            on_status("Using fast Lanczos upscale (safe mode)…")
        target = (w0 * scale, h0 * scale)
        max_side = settings.max_output_side
        if max(target) > max_side:
            s = max_side / float(max(target))
            target = (max(1, int(target[0] * s)), max(1, int(target[1] * s)))
        return rgba.resize(target, Image.Resampling.LANCZOS)


@lru_cache(maxsize=1)
def get_realesrgan_service() -> RealESRGANService:
    return RealESRGANService()
