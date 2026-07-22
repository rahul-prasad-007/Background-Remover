from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image


def load_image(path: Path | str | bytes) -> Image.Image:
    """Load an image and ensure RGBA for print-safe transparency handling."""
    if isinstance(path, bytes):
        image = Image.open(io.BytesIO(path))
    else:
        image = Image.open(path)
    image.load()
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")
    return image


def pil_to_cv(image: Image.Image) -> np.ndarray:
    """Convert PIL image to OpenCV BGRA/BGR array."""
    arr = np.array(image)
    if image.mode == "RGBA":
        return arr[:, :, [2, 1, 0, 3]].copy()
    if image.mode == "RGB":
        return arr[:, :, ::-1].copy()
    raise ValueError(f"Unsupported mode: {image.mode}")


def cv_to_pil(array: np.ndarray) -> Image.Image:
    """Convert OpenCV BGR/BGRA array to PIL RGB/RGBA."""
    if array.ndim != 3:
        raise ValueError("Expected HxWxC array")
    if array.shape[2] == 4:
        rgba = array[:, :, [2, 1, 0, 3]]
        return Image.fromarray(rgba, mode="RGBA")
    if array.shape[2] == 3:
        rgb = array[:, :, ::-1]
        return Image.fromarray(rgb, mode="RGB")
    raise ValueError(f"Unsupported channel count: {array.shape[2]}")


def ensure_rgba(image: Image.Image) -> Image.Image:
    if image.mode == "RGBA":
        return image
    return image.convert("RGBA")


def save_transparent_png(image: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_rgba(image).save(path, format="PNG", optimize=True)
    return path
