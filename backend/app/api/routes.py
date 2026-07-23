from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import AsyncGenerator

import aiofiles
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.config import settings
from app.schemas import PipelineStage, ProgressEvent
from app.services.pipeline import get_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["process"])

# In-memory job registry (single-node production; swap for Redis if scaling)
_jobs: dict[str, Path] = {}


def _validate_upload(file: UploadFile, size: int) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    # Prevent path tricks in the original filename; we store by job_id only
    name = Path(file.filename).name
    suffix = Path(name).suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Allowed: {', '.join(sorted(settings.allowed_extensions))}",
        )

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if size > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds {settings.max_file_size_mb} MB limit",
        )
    if size < 32:
        raise HTTPException(status_code=400, detail="File is empty or too small")


@router.post("/process")
async def process_image(
    file: UploadFile = File(...),
    quality: str = Form("auto"),
    scale: int | None = Form(None),
) -> StreamingResponse:
    """
    Accept multipart image + quality mode.
    quality: auto | original | 2 | 4
    (scale kept for backward compatibility)
    """
    raw = await file.read()
    _validate_upload(file, len(raw))

    mode = (quality or "auto").strip().lower()
    if scale is not None and mode == "auto":
        # legacy clients sending only scale=
        mode = "4" if int(scale) >= 4 else "2"
    if mode not in {"auto", "original", "2", "4"}:
        mode = "auto"

    if settings.bg_provider == "removebg" and not (settings.remove_bg_api_key or "").strip():
        raise HTTPException(
            status_code=500,
            detail="BG_PROVIDER=removebg but REMOVE_BG_API_KEY is not set in backend/.env",
        )

    job_id = uuid.uuid4().hex
    suffix = Path(Path(file.filename or "upload.png").name).suffix.lower() or ".png"
    if suffix not in settings.allowed_extensions:
        suffix = ".png"
    upload_path = settings.upload_dir / f"{job_id}{suffix}"
    output_path = settings.output_dir / f"{job_id}.png"

    async with aiofiles.open(upload_path, "wb") as out:
        await out.write(raw)

    queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_progress(event: ProgressEvent) -> None:
        # Register result as soon as the pipeline marks complete (before stream ends)
        if event.stage == PipelineStage.COMPLETE and output_path.exists():
            _jobs[job_id] = output_path
        loop.call_soon_threadsafe(queue.put_nowait, event)

    async def run_pipeline() -> None:
        try:
            await asyncio.to_thread(
                get_pipeline().process,
                upload_path,
                output_path,
                job_id,
                on_progress,
                mode,
            )
            if output_path.exists():
                _jobs[job_id] = output_path
        except Exception as exc:  # noqa: BLE001
            logger.exception("Pipeline failed for job %s", job_id)
            error_event = ProgressEvent(
                stage=PipelineStage.ERROR,
                label="Error",
                status="error",
                progress=0,
                message=str(exc),
                job_id=job_id,
            )
            loop.call_soon_threadsafe(queue.put_nowait, error_event)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    async def event_stream() -> AsyncGenerator[str, None]:
        task = asyncio.create_task(run_pipeline())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                payload = event.model_dump()
                yield f"data: {json.dumps(payload)}\n\n"
        finally:
            await task

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/download/{job_id}")
async def download_result(job_id: str) -> FileResponse:
    # Always prefer disk — survives server reloads (in-memory map is cleared)
    safe_id = Path(job_id).name  # prevent path traversal
    candidate = settings.output_dir / f"{safe_id}.png"
    path = _jobs.get(safe_id)
    if path is None or not path.exists():
        path = candidate if candidate.exists() else None

    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Result not found. Process the image again.")

    return FileResponse(
        path,
        media_type="image/png",
        filename=f"print-ready-{safe_id}.png",
        headers={
            "Cache-Control": "no-store",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
