from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PIL import Image

from app.config import settings
from app.schemas import STAGE_LABELS, PipelineStage, ProgressCallback, ProgressEvent
from app.services.background import get_background_service
from app.services.face_detection import get_face_detection_service
from app.services.gfpgan_service import get_gfpgan_service
from app.services.opencv_enhance import get_opencv_enhance_service
from app.services.realesrgan_service import get_realesrgan_service
from app.utils.image_utils import ensure_rgba, load_image, save_transparent_png
from app.utils.memory import free_memory

logger = logging.getLogger(__name__)


def _cap_side(image: Image.Image, max_side: int) -> Image.Image:
    rgba = ensure_rgba(image)
    w, h = rgba.size
    if max(w, h) <= max_side:
        return rgba
    scale = max_side / float(max(w, h))
    size = (max(1, int(w * scale)), max(1, int(h * scale)))
    logger.info("Resize %sx%s → %sx%s", w, h, *size)
    return rgba.resize(size, Image.Resampling.LANCZOS)


class ImagePipeline:
    """
    remove.bg (full quality) → Faces → GFPGAN → Real-ESRGAN → OpenCV → PNG
    """

    def process(
        self,
        source: Path | bytes,
        output_path: Path,
        job_id: str,
        on_progress: Optional[ProgressCallback] = None,
        quality: str = "auto",
    ) -> Path:
        mode = (quality or "auto").strip().lower()
        if mode not in {"auto", "original", "2", "4"}:
            mode = "auto"

        def emit(
            stage: PipelineStage,
            status: str,
            progress: float,
            message: str | None = None,
            faces_found: int | None = None,
            download_url: str | None = None,
        ) -> None:
            if on_progress is None:
                return
            on_progress(
                ProgressEvent(
                    stage=stage,
                    label=STAGE_LABELS[stage],
                    status=status,
                    progress=progress,
                    message=message,
                    faces_found=faces_found,
                    download_url=download_url,
                    job_id=job_id,
                )
            )

        emit(PipelineStage.UPLOADING, "done", 5, "Image received")

        # Always cap early for 8GB PCs — prevents sudden OOM crashes
        image = ensure_rgba(load_image(source))
        if max(image.size) > settings.safe_input_side:
            emit(
                PipelineStage.UPLOADING,
                "done",
                8,
                f"Auto-resized for low RAM (max {settings.safe_input_side}px)",
            )
        image = _cap_side(image, settings.safe_input_side)
        free_memory("load")

        # 1. Background removal (local unlimited OR remove.bg)
        provider = settings.bg_provider
        emit(
            PipelineStage.REMOVING_BACKGROUND,
            "active",
            10,
            (
                "Local BiRefNet (unlimited)…"
                if provider != "removebg"
                else "Connecting to remove.bg…"
            ),
        )

        def bg_status(message: str) -> None:
            emit(PipelineStage.REMOVING_BACKGROUND, "active", 18, message)

        image = get_background_service().remove_background(image, on_status=bg_status)
        emit(
            PipelineStage.REMOVING_BACKGROUND,
            "done",
            30,
            "Background removed + edges cleaned",
        )
        free_memory("background")

        # Resolve upscale AFTER we know cutout size
        if mode == "original":
            scale = 0
        elif mode == "4":
            scale = 4
        elif mode == "2":
            scale = 2
        else:
            # Auto: prefer ×2 so subjects look big & clear like catalog cutouts
            scale = 2 if max(image.size) < 2200 else 0

        logger.info(
            "Job %s cutout %sx%s | quality=%s | esrgan=×%s",
            job_id,
            image.width,
            image.height,
            mode,
            scale if scale else "skip (sharpen only)",
        )

        # 2. Face detection
        emit(PipelineStage.DETECTING_FACES, "active", 35, "Scanning for faces")
        faces = get_face_detection_service().detect(image)
        face_count = len(faces)
        emit(
            PipelineStage.DETECTING_FACES,
            "done",
            45,
            f"Found {face_count} face(s)" if face_count else "No faces detected",
            faces_found=face_count,
        )
        free_memory("face detect")

        # 3. GFPGAN only if faces exist
        if face_count > 0:
            emit(
                PipelineStage.RESTORING_FACES,
                "active",
                50,
                "Restoring faces",
                faces_found=face_count,
            )
            image = get_gfpgan_service().restore(image)
            emit(
                PipelineStage.RESTORING_FACES,
                "done",
                65,
                "Faces restored",
                faces_found=face_count,
            )
        else:
            emit(
                PipelineStage.RESTORING_FACES,
                "skipped",
                65,
                "Skipped — no faces detected",
                faces_found=0,
            )
        free_memory("faces")

        # 4. Real-ESRGAN (optional) — cap input for RAM on 8GB PCs
        if scale == 0:
            emit(
                PipelineStage.ENHANCING_IMAGE,
                "skipped",
                85,
                "Skipped upscale — applying print sharpening instead",
            )
        else:
            emit(
                PipelineStage.ENHANCING_IMAGE,
                "active",
                70,
                f"Upscaling with Real-ESRGAN ×{scale}",
            )
            image = _cap_side(
                image,
                settings.realesrgan_4x_max_input
                if scale == 4
                else settings.realesrgan_2x_max_input,
            )

            def esrgan_status(message: str) -> None:
                emit(PipelineStage.ENHANCING_IMAGE, "active", 78, message)

            image = get_realesrgan_service().upscale(
                image, scale=scale, on_status=esrgan_status
            )
            emit(
                PipelineStage.ENHANCING_IMAGE,
                "done",
                85,
                f"Upscaled ×{scale} with Real-ESRGAN",
            )
        free_memory("upscale")

        # 5. OpenCV post-processing (always — this is what makes it "HD punchy")
        emit(PipelineStage.FINALIZING, "active", 90, "Catalog polish — clean edges & clarity…")
        image = get_opencv_enhance_service().enhance(image)
        save_transparent_png(image, output_path)
        emit(PipelineStage.FINALIZING, "done", 97, "Print-ready PNG written")
        free_memory("finalize")

        emit(
            PipelineStage.COMPLETE,
            "done",
            100,
            "Processing complete",
            download_url=f"/api/download/{job_id}",
        )
        logger.info("Pipeline complete for job %s → %s", job_id, output_path)
        return output_path


def get_pipeline() -> ImagePipeline:
    return ImagePipeline()
