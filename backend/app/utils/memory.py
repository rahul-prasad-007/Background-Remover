from __future__ import annotations

import gc
import logging

logger = logging.getLogger(__name__)


def free_memory(label: str | None = None) -> None:
    """Aggressively release RAM between pipeline stages (critical on 8GB PCs)."""
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        # Drop cached allocator fragmentation on CPU builds too
        try:
            torch._C._cuda_clearCublasWorkspaces()  # type: ignore[attr-defined]
        except Exception:
            pass
    except Exception:  # noqa: BLE001
        pass
    gc.collect()
    if label:
        logger.info("Freed memory after: %s", label)


def is_oom_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "out of memory",
            "not enough memory",
            "failed to allocate",
            "allocate memory",
            "oom",
            "std::bad_alloc",
            "memoryerror",
        )
    ) or isinstance(exc, MemoryError)
