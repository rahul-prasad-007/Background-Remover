from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from app.utils.image_utils import ensure_rgba


def pad_for_cutout(image: Image.Image, pad: int = 40) -> tuple[Image.Image, int]:
    """Add a border so subjects touching the frame edge are not clipped."""
    rgba = ensure_rgba(image)
    if pad <= 0:
        return rgba, 0
    w, h = rgba.size
    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (255, 255, 255, 255))
    canvas.paste(rgba, (pad, pad), rgba)
    return canvas, pad


def unpad_cutout(image: Image.Image, pad: int) -> Image.Image:
    if pad <= 0:
        return image
    w, h = image.size
    return image.crop((pad, pad, w - pad, h - pad))


def fill_tiny_pinholes(alpha: np.ndarray, max_hole_area: int = 64) -> np.ndarray:
    """Fill only tiny compression pinholes — never collage gaps."""
    a = alpha.astype(np.uint8)
    mask = (a > 90).astype(np.uint8) * 255
    h, w = mask.shape

    inv = cv2.bitwise_not(mask)
    flood = inv.copy()
    ff = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(flood, ff, (0, 0), 0)
    holes = cv2.bitwise_and(inv, cv2.bitwise_not(flood))

    num, labels, stats, _ = cv2.connectedComponentsWithStats(
        (holes > 0).astype(np.uint8), connectivity=8
    )
    out = a.copy()
    for i in range(1, num):
        if int(stats[i, cv2.CC_STAT_AREA]) <= max_hole_area:
            out[labels == i] = np.maximum(out[labels == i], 250)
    return out


def clear_white_and_gap_background(
    rgb: np.ndarray,
    alpha: np.ndarray,
    white_thresh: int = 242,
) -> tuple[np.ndarray, np.ndarray]:
    """Punch white paper / collage gaps to transparency (keep textured white fur)."""
    alpha = alpha.astype(np.float32).copy()
    rgb_f = rgb.astype(np.float32)
    h, w = alpha.shape

    near_white = (
        (rgb[:, :, 0] >= white_thresh)
        & (rgb[:, :, 1] >= white_thresh)
        & (rgb[:, :, 2] >= white_thresh)
    )
    mx = rgb_f.max(axis=2)
    mn = rgb_f.min(axis=2)
    low_chroma = (mx - mn) < 18

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    local_var = cv2.blur(gray * gray, (5, 5)) - cv2.blur(gray, (5, 5)) ** 2
    flat = local_var < 40
    paper = near_white & low_chroma & flat

    seed = (paper | (near_white & (alpha < 180))).astype(np.uint8) * 255
    flood = seed.copy()
    ff = np.zeros((h + 2, w + 2), np.uint8)
    for x in range(0, w, max(1, w // 32)):
        if seed[0, x]:
            cv2.floodFill(flood, ff, (x, 0), 128)
        if seed[h - 1, x]:
            cv2.floodFill(flood, ff, (x, h - 1), 128)
    for y in range(0, h, max(1, h // 32)):
        if seed[y, 0]:
            cv2.floodFill(flood, ff, (0, y), 128)
        if seed[y, w - 1]:
            cv2.floodFill(flood, ff, (w - 1, y), 128)

    border_white = flood == 128
    enclosed_gaps = paper & ~border_white
    unsure_white = near_white & (alpha < 200)
    bg = border_white | enclosed_gaps | unsure_white
    alpha[bg] = 0

    haze = near_white & (alpha > 0) & (alpha < 230) & low_chroma & flat
    alpha[haze] = 0

    out_rgb = rgb.copy()
    out_rgb[alpha < 2] = 0
    return out_rgb, np.clip(alpha, 0, 255).astype(np.uint8)


def refine_alpha_catalog(alpha: np.ndarray, rgb: np.ndarray) -> np.ndarray:
    """
    Catalog-clean matte: smooth mask, then harden body while keeping soft hair tips.
    Matches print cutouts (rhino / animals) — crisp silhouette, no mushy fringe.
    """
    a = alpha.astype(np.float32)
    guide = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    # Edge-aware smooth if available; else bilateral
    try:
        a = cv2.ximgproc.guidedFilter(
            guide=guide, src=a.astype(np.uint8), radius=4, eps=50.0, dDepth=-1
        ).astype(np.float32)
    except Exception:
        a = cv2.bilateralFilter(a.astype(np.uint8), d=5, sigmaColor=40, sigmaSpace=40).astype(
            np.float32
        )

    # Smoothstep harden: kill weak BG, keep strong FG solid
    low, high = 28.0, 185.0
    t = np.clip((a - low) / (high - low), 0.0, 1.0)
    t = t * t * (3.0 - 2.0 * t)
    a = t * 255.0

    # Tiny morphological close on solid core (fills micro gaps on body only)
    solid = (a >= 230).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    solid = cv2.morphologyEx(solid, cv2.MORPH_CLOSE, k, iterations=1)
    a = np.maximum(a, solid.astype(np.float32) * 0.98)

    # Anti-alias 1px on final silhouette
    h, w = a.shape
    big = cv2.resize(a, (w * 2, h * 2), interpolation=cv2.INTER_LINEAR)
    big = cv2.GaussianBlur(big, (0, 0), sigmaX=0.35)
    a = cv2.resize(big, (w, h), interpolation=cv2.INTER_AREA)
    return np.clip(a, 0, 255).astype(np.uint8)


def defringe_from_interior(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """
    Remove grass / sky color spill on the cutout edge by pulling colors
    from the opaque interior (catalog-style clean rim).
    """
    a = alpha.astype(np.float32) / 255.0
    mask = (a >= 0.85).astype(np.float32)
    if mask.sum() < 50:
        return rgb

    rgb_f = rgb.astype(np.float32)
    ksize = 9
    clean = np.empty_like(rgb_f)
    den = cv2.blur(mask, (ksize, ksize)) + 1e-5
    for c in range(3):
        clean[:, :, c] = cv2.blur(rgb_f[:, :, c] * mask, (ksize, ksize)) / den

    # Fringe = present but not deep interior
    present = (a > 0.08).astype(np.float32)
    core = cv2.erode((a >= 0.92).astype(np.uint8) * 255, np.ones((5, 5), np.uint8), 1)
    core_f = core.astype(np.float32) / 255.0
    fringe = np.clip(present - core_f, 0, 1)
    fringe = cv2.GaussianBlur(fringe, (0, 0), sigmaX=0.8)

    # Stronger pull on high-chroma spill (green grass, blue sky)
    chroma = rgb_f.max(axis=2) - rgb_f.min(axis=2)
    spill = np.clip((chroma - 25.0) / 60.0, 0.0, 1.0) * fringe
    mix = np.clip(fringe * 0.65 + spill * 0.45, 0.0, 0.95)[:, :, None]

    out = rgb_f * (1.0 - mix) + clean * mix
    out = np.clip(out, 0, 255).astype(np.uint8)
    out[alpha < 2] = 0
    return out


def remove_interior_white_specks(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """
    Kill bright white blotches / noise inside the subject caused by oversharpening.
    Replaces outlier bright pixels with a local median of the subject.
    """
    subject = alpha >= 180
    if not np.any(subject):
        return rgb

    out = rgb.copy()
    gray = cv2.cvtColor(out, cv2.COLOR_RGB2GRAY).astype(np.float32)
    med = cv2.medianBlur(out, 5)
    med_g = cv2.cvtColor(med, cv2.COLOR_RGB2GRAY).astype(np.float32)

    # Bright outliers vs local median (classic "white speck" pattern)
    bright = (gray - med_g) > 28
    near_white = (out[:, :, 0] > 210) & (out[:, :, 1] > 210) & (out[:, :, 2] > 210)
    hot = subject & (bright | (near_white & ((gray - med_g) > 12)))

    if np.any(hot):
        out[hot] = med[hot]

    # Soft highlight roll-off — stop chalky blown patches
    g = cv2.cvtColor(out, cv2.COLOR_RGB2GRAY).astype(np.float32)
    over = subject & (g > 225)
    if np.any(over):
        soft = cv2.GaussianBlur(out, (0, 0), sigmaX=1.2)
        # Pull only the hottest pixels down a bit
        t = np.clip((g - 225.0) / 30.0, 0.0, 1.0)[:, :, None]
        t = t * over[:, :, None].astype(np.float32)
        out = np.clip(
            out.astype(np.float32) * (1.0 - t * 0.55) + soft.astype(np.float32) * (t * 0.55),
            0,
            255,
        ).astype(np.uint8)

    return out


def enhance_subject_catalog(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Gentle clarity only — no CLAHE/vibrance (those caused white speckles + purple cast)."""
    mask = (alpha.astype(np.float32) / 255.0)[:, :, None]
    if mask.max() < 0.01:
        return rgb

    base = rgb.astype(np.float32)

    # Very light unsharp on deep interior only
    blur = cv2.GaussianBlur(base, (0, 0), sigmaX=0.85)
    sharp = np.clip(base * 1.12 + blur * (1.0 - 1.12), 0, 255)

    solid = (alpha >= 210).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    core = cv2.erode(solid, k, iterations=2).astype(np.float32) / 255.0
    core = cv2.GaussianBlur(core, (0, 0), sigmaX=1.4)[:, :, None]

    out = base * (1.0 - core * 0.75) + sharp * (core * 0.75)
    out = np.clip(out, 0, 255).astype(np.uint8)
    out = remove_interior_white_specks(out, alpha)
    out[alpha < 2] = 0  # black under transparency — no white flash on dark preview
    return out


def trim_to_subject(image: Image.Image, pad_ratio: float = 0.06, min_pad: int = 24) -> Image.Image:
    """Crop empty transparent margins so the subject looks big in frame (catalog crop)."""
    rgba = ensure_rgba(image)
    alpha = np.array(rgba.split()[-1])
    ys, xs = np.where(alpha > 12)
    if len(xs) == 0 or len(ys) == 0:
        return rgba
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    pad = max(min_pad, int(max(bw, bh) * pad_ratio))
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(rgba.width - 1, x1 + pad)
    y1 = min(rgba.height - 1, y1 + pad)
    return rgba.crop((x0, y0, x1 + 1, y1 + 1))


def apply_mask_keep_original_colors(
    original: Image.Image,
    mask_source: Image.Image,
) -> Image.Image:
    """ORIGINAL RGB + refined cutout alpha (catalog edges)."""
    orig = ensure_rgba(original)
    cut = ensure_rgba(mask_source)
    alpha = np.array(cut.split()[-1])
    if alpha.shape[1] != orig.size[0] or alpha.shape[0] != orig.size[1]:
        alpha = cv2.resize(alpha, orig.size, interpolation=cv2.INTER_LINEAR)

    alpha = fill_tiny_pinholes(alpha, max_hole_area=64)
    rgb = np.array(orig.convert("RGB"))
    rgb, alpha = clear_white_and_gap_background(rgb, alpha)
    alpha = refine_alpha_catalog(alpha, rgb)
    rgb = defringe_from_interior(rgb, alpha)
    rgb = remove_interior_white_specks(rgb, alpha)
    rgb, alpha = clear_white_and_gap_background(rgb, alpha)
    # Transparent = black RGB (clean on dark boards); white gaps stay alpha=0
    rgb = rgb.copy()
    rgb[alpha < 2] = 0
    return Image.fromarray(np.dstack([rgb, alpha]), mode="RGBA")


def decontaminate_edges(image: Image.Image, erode_px: int = 1) -> Image.Image:
    """Catalog fringe cleanup after cutout."""
    rgba = ensure_rgba(image)
    arr = np.array(rgba)
    rgb = arr[:, :, :3].copy()
    alpha = arr[:, :, 3].copy()
    rgb, alpha = clear_white_and_gap_background(rgb, alpha)
    alpha = refine_alpha_catalog(alpha, rgb)
    rgb = defringe_from_interior(rgb, alpha)
    rgb = remove_interior_white_specks(rgb, alpha)
    rgb[alpha < 2] = 0
    _ = erode_px  # kept for API compat
    return Image.fromarray(np.dstack([rgb, alpha]), mode="RGBA")


def polish_for_zoom(image: Image.Image) -> Image.Image:
    """
    Final print polish → big, clear, clean catalog cutout:
      refined matte · defringe · gentle clarity · no white speckles · tight crop
    """
    rgba = ensure_rgba(image)
    arr = np.array(rgba)
    rgb, alpha = arr[:, :, :3], arr[:, :, 3]
    alpha = fill_tiny_pinholes(alpha, max_hole_area=64)
    rgb, alpha = clear_white_and_gap_background(rgb, alpha)
    alpha = refine_alpha_catalog(alpha, rgb)
    rgb = defringe_from_interior(rgb, alpha)
    rgb = enhance_subject_catalog(rgb, alpha)
    rgb = remove_interior_white_specks(rgb, alpha)
    rgb, alpha = clear_white_and_gap_background(rgb, alpha)
    rgb = rgb.copy()
    rgb[alpha < 2] = 0
    out = Image.fromarray(np.dstack([rgb, alpha]), mode="RGBA")
    return trim_to_subject(out, pad_ratio=0.07, min_pad=28)


def unsharp_rgba(image: Image.Image, amount: float = 1.3, radius: float = 0.9) -> Image.Image:
    rgba = ensure_rgba(image)
    arr = np.array(rgba)
    rgb = enhance_subject_catalog(arr[:, :, :3], arr[:, :, 3])
    return Image.fromarray(np.dstack([rgb, arr[:, :, 3]]), mode="RGBA")


def fill_alpha_holes(alpha: np.ndarray) -> np.ndarray:
    return fill_tiny_pinholes(alpha, max_hole_area=64)
