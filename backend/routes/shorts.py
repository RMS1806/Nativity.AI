"""
Shorts API — generate, browse, and localize short clips extracted from localized videos.

POST /api/shorts/generate          — kick off clip generation for a source job
GET  /api/shorts/sources           — list source jobs that have shorts
GET  /api/shorts/source/{job_id}   — list clips for one source
DELETE /api/shorts/{short_id}      — delete a clip
"""

import threading
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from fastapi import Depends
from dependencies import get_current_user
from services.db_service import db_service
from services.s3_service import s3_service
from tasks import _run_shorts_generation

router = APIRouter(prefix="/api/shorts", tags=["shorts"])


# ── Request models ────────────────────────────────────────────────────────────

class GenerateShortsRequest(BaseModel):
    source_job_id: str
    target_count: int = 5


# ── Helpers ───────────────────────────────────────────────────────────────────

def _presign(s3_key: Optional[str]) -> Optional[str]:
    if not s3_key:
        return None
    result = s3_service.generate_presigned_download_url(s3_key)
    return result.get("download_url")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_shorts(
    req: GenerateShortsRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """
    Kick off shorts generation for a completed source job.
    Returns immediately; extraction runs in background.
    """
    user_id: str = user["sub"]
    source = db_service.get_job_by_id(req.source_job_id)
    if not source or source.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Source job not found")
    if source.get("status") != "complete":
        raise HTTPException(status_code=400, detail="Source job is not complete yet")

    def run():
        _run_shorts_generation(req.source_job_id, user_id, req.target_count)

    t = threading.Thread(target=run, daemon=True)
    t.start()

    return {
        "success": True,
        "message": f"Generating up to {req.target_count} shorts in the background",
        "source_job_id": req.source_job_id,
    }


@router.get("/sources")
async def list_sources(user: dict = Depends(get_current_user)):
    """Return all source videos that have at least one short."""
    user_id: str = user["sub"]
    sources = db_service.get_user_shorts_sources(user_id)
    return {"success": True, "sources": sources, "count": len(sources)}


@router.get("/source/{source_job_id}")
async def list_shorts_for_source(
    source_job_id: str,
    user: dict = Depends(get_current_user),
):
    """Return all clips extracted from one source job."""
    user_id: str = user["sub"]
    shorts = db_service.get_shorts_for_source(source_job_id, user_id)
    enriched = []
    for s in shorts:
        s["clip_url"] = _presign(s.get("s3_key"))
        enriched.append(s)
    return {"success": True, "shorts": enriched, "count": len(enriched)}


@router.delete("/{short_id}")
async def delete_short(
    short_id: str,
    user: dict = Depends(get_current_user),
):
    user_id: str = user["sub"]
    short = db_service.get_short_by_id(short_id, user_id)
    if not short:
        raise HTTPException(status_code=404, detail="Short not found")

    s3_key = short.get("s3_key")
    if s3_key:
        try:
            s3_service.delete_file(s3_key)
        except Exception:
            pass

    result = db_service.delete_short(short_id, user_id)
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return {"success": True}
