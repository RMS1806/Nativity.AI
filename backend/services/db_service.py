"""
PostgreSQL Service for Nativity.ai
Persistent storage of video localization jobs + history.

Drop-in replacement for the previous DynamoDB service: every public method keeps
the same signature and return shape, so routes / job_service / worker are unchanged.

Table: videos  (one row per job_id)  — see scripts/schema.sql
JSON columns (cultural_report, cultural_analysis, draft_segments) are stored as
TEXT containing json.dumps(...) output, exactly like the old store, so callers
that do json.loads(...) keep working unchanged.
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from config import settings


class DBService:
    """PostgreSQL-backed store for video jobs and history."""

    def __init__(self):
        self._pool: Optional[ThreadedConnectionPool] = None

    # ── Connection management ────────────────────────────────────────────
    def _get_pool(self) -> Optional[ThreadedConnectionPool]:
        """Lazily create a thread-safe connection pool (API + worker threads)."""
        if self._pool is None and settings.DATABASE_URL:
            self._pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=settings.DATABASE_URL,
            )
        return self._pool

    def is_configured(self) -> bool:
        """True if a DATABASE_URL is set."""
        return bool(settings.DATABASE_URL)

    def _execute(self, query: str, params: tuple = (), *, fetch: str = None):
        """
        Run a query. fetch: None (no return), 'one', 'all'.
        Returns rows as dicts (RealDictCursor). Commits/rolls back automatically.
        """
        pool = self._get_pool()
        if not pool:
            raise RuntimeError("DATABASE_URL not configured")
        conn = pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                result = None
                if fetch == "one":
                    result = cur.fetchone()
                elif fetch == "all":
                    result = cur.fetchall()
                rowcount = cur.rowcount
            conn.commit()
            return result, rowcount
        except Exception:
            conn.rollback()
            raise
        finally:
            pool.putconn(conn)

    # ── Writes ───────────────────────────────────────────────────────────
    def save_video(
        self,
        user_id: str,
        job_id: str,
        target_language: str,
        input_file: str,
        status: str = "complete",
        output_url: Optional[str] = None,
        whatsapp_url: Optional[str] = None,
        file_size_mb: Optional[float] = None,
        cultural_report: Optional[Dict[str, Any]] = None,
        cultural_analysis: Optional[List[Dict[str, Any]]] = None,
        segments_count: Optional[int] = None,
        draft_segments: Optional[List[Dict[str, Any]]] = None,
        output_s3_key: Optional[str] = None,
        subtitle_s3_key: Optional[str] = None,
        words_localized: Optional[int] = None,
        progress: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upsert a job row keyed on job_id. Provided fields overwrite; optional
        fields left as None are preserved (COALESCE) so partial updates don't
        wipe data written by an earlier call.
        """
        if not self.is_configured():
            return {"error": "Database not configured"}

        now = datetime.utcnow().isoformat() + "Z"
        params = {
            "job_id": job_id,
            "user_id": user_id,
            "target_language": target_language,
            "input_file": input_file,
            "status": status,
            "created_at": now,
            "updated_at": now,
            "output_url": output_url,
            "output_s3_key": output_s3_key,
            "subtitle_s3_key": subtitle_s3_key,
            "whatsapp_url": whatsapp_url,
            "file_size_mb": float(file_size_mb) if file_size_mb is not None else None,
            "segments_count": segments_count,
            "words_localized": words_localized,
            "progress": progress,
            "error_message": error_message,
            "cultural_report": json.dumps(cultural_report) if cultural_report else None,
            "cultural_analysis": json.dumps(cultural_analysis) if cultural_analysis else None,
            "draft_segments": json.dumps(draft_segments) if draft_segments else None,
        }

        query = """
            INSERT INTO videos (
                job_id, user_id, target_language, input_file, status,
                created_at, updated_at, output_url, output_s3_key, subtitle_s3_key,
                whatsapp_url, file_size_mb, segments_count, words_localized, progress,
                error_message, cultural_report, cultural_analysis, draft_segments
            ) VALUES (
                %(job_id)s, %(user_id)s, %(target_language)s, %(input_file)s, %(status)s,
                %(created_at)s, %(updated_at)s, %(output_url)s, %(output_s3_key)s, %(subtitle_s3_key)s,
                %(whatsapp_url)s, %(file_size_mb)s, %(segments_count)s, %(words_localized)s, %(progress)s,
                %(error_message)s, %(cultural_report)s, %(cultural_analysis)s, %(draft_segments)s
            )
            ON CONFLICT (job_id) DO UPDATE SET
                user_id           = EXCLUDED.user_id,
                target_language   = EXCLUDED.target_language,
                input_file        = EXCLUDED.input_file,
                status            = EXCLUDED.status,
                updated_at        = EXCLUDED.updated_at,
                output_url        = COALESCE(EXCLUDED.output_url, videos.output_url),
                output_s3_key     = COALESCE(EXCLUDED.output_s3_key, videos.output_s3_key),
                subtitle_s3_key   = COALESCE(EXCLUDED.subtitle_s3_key, videos.subtitle_s3_key),
                whatsapp_url      = COALESCE(EXCLUDED.whatsapp_url, videos.whatsapp_url),
                file_size_mb      = COALESCE(EXCLUDED.file_size_mb, videos.file_size_mb),
                segments_count    = COALESCE(EXCLUDED.segments_count, videos.segments_count),
                words_localized   = COALESCE(EXCLUDED.words_localized, videos.words_localized),
                progress          = COALESCE(EXCLUDED.progress, videos.progress),
                error_message     = COALESCE(EXCLUDED.error_message, videos.error_message),
                cultural_report   = COALESCE(EXCLUDED.cultural_report, videos.cultural_report),
                cultural_analysis = COALESCE(EXCLUDED.cultural_analysis, videos.cultural_analysis),
                draft_segments    = COALESCE(EXCLUDED.draft_segments, videos.draft_segments)
        """
        try:
            self._execute(query, params)
            return {"success": True, "job_id": job_id}
        except Exception as e:
            return {"error": str(e)}

    def update_job_segments(
        self,
        user_id: str,
        job_id: str,
        segments: List[Dict[str, Any]],
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update the segments (and optionally status) for a job."""
        if not self.is_configured():
            return {"error": "Database not configured"}

        now = datetime.utcnow().isoformat() + "Z"
        sets = ["draft_segments = %s", "updated_at = %s"]
        params: list = [json.dumps(segments), now]
        if status:
            sets.append("status = %s")
            params.append(status)
        params.extend([user_id, job_id])
        query = f"UPDATE videos SET {', '.join(sets)} WHERE user_id = %s AND job_id = %s"
        try:
            _, rowcount = self._execute(query, tuple(params))
            if rowcount == 0:
                return {"error": "Video not found"}
            return {"success": True, "job_id": job_id}
        except Exception as e:
            return {"error": str(e)}

    def update_job_status(
        self,
        user_id: str,
        job_id: str,
        status: str,
        output_url: Optional[str] = None,
        output_s3_key: Optional[str] = None,
        subtitle_s3_key: Optional[str] = None,
        approved_segments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Update status and optional output fields for a job."""
        if not self.is_configured():
            return {"error": "Database not configured"}

        now = datetime.utcnow().isoformat() + "Z"
        sets = ["status = %s", "updated_at = %s"]
        params: list = [status, now]
        if output_url:
            sets.append("output_url = %s")
            params.append(output_url)
        if output_s3_key:
            sets.append("output_s3_key = %s")
            params.append(output_s3_key)
        if subtitle_s3_key:
            sets.append("subtitle_s3_key = %s")
            params.append(subtitle_s3_key)
        if approved_segments is not None:
            sets.append("draft_segments = %s")
            params.append(json.dumps(approved_segments))
        params.extend([user_id, job_id])
        query = f"UPDATE videos SET {', '.join(sets)} WHERE user_id = %s AND job_id = %s"
        try:
            _, rowcount = self._execute(query, tuple(params))
            if rowcount == 0:
                return {"error": "Video not found"}
            return {"success": True, "job_id": job_id}
        except Exception as e:
            return {"error": str(e)}

    def update_job_progress(
        self,
        user_id: str,
        job_id: str,
        progress: int,
        message: str,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update progress + message (and optionally status) for a job."""
        if not self.is_configured():
            return {"error": "Database not configured"}

        now = datetime.utcnow().isoformat() + "Z"
        sets = ["progress = %s", "message = %s", "updated_at = %s"]
        params: list = [progress, message, now]
        if status:
            sets.append("status = %s")
            params.append(status)
        params.extend([user_id, job_id])
        query = f"UPDATE videos SET {', '.join(sets)} WHERE user_id = %s AND job_id = %s"
        try:
            _, rowcount = self._execute(query, tuple(params))
            if rowcount == 0:
                return {"error": "Job not found"}
            return {"success": True, "job_id": job_id}
        except Exception as e:
            return {"error": str(e)}

    def delete_video(self, user_id: str, job_id: str) -> Dict[str, Any]:
        """Delete a job row (only if owned by user)."""
        if not self.is_configured():
            return {"error": "Database not configured"}
        try:
            _, rowcount = self._execute(
                "DELETE FROM videos WHERE user_id = %s AND job_id = %s",
                (user_id, job_id),
            )
            if rowcount == 0:
                return {"error": "Video not found or not owned by user"}
            return {"success": True, "deleted_job_id": job_id}
        except Exception as e:
            return {"error": str(e)}

    # ── Reads ────────────────────────────────────────────────────────────
    def get_user_history(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """Return a user's videos (newest first)."""
        if not self.is_configured():
            return {"error": "Database not configured"}
        try:
            rows, _ = self._execute(
                """
                SELECT * FROM videos
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
                fetch="all",
            )
            videos = []
            for row in (rows or []):
                video = {
                    "job_id": row.get("job_id"),
                    "target_language": row.get("target_language"),
                    "input_file": row.get("input_file"),
                    "status": row.get("status"),
                    "created_at": row.get("created_at"),
                    "output_url": row.get("output_url"),
                    "output_s3_key": row.get("output_s3_key"),
                    "subtitle_s3_key": row.get("subtitle_s3_key"),
                    "words_localized": int(row["words_localized"]) if row.get("words_localized") is not None else None,
                    "whatsapp_url": row.get("whatsapp_url"),
                    "file_size_mb": float(row["file_size_mb"]) if row.get("file_size_mb") is not None else None,
                    "segments_count": row.get("segments_count"),
                }
                if row.get("cultural_report"):
                    try:
                        video["cultural_report"] = json.loads(row["cultural_report"])
                    except (json.JSONDecodeError, TypeError):
                        video["cultural_report"] = None
                videos.append(video)
            return {"success": True, "videos": videos, "count": len(videos)}
        except Exception as e:
            return {"error": str(e)}

    def get_video_by_job_id(self, user_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """Return the raw row for a job owned by user (JSON cols are strings)."""
        if not self.is_configured():
            return None
        try:
            row, _ = self._execute(
                "SELECT * FROM videos WHERE user_id = %s AND job_id = %s",
                (user_id, job_id),
                fetch="one",
            )
            return dict(row) if row else None
        except Exception:
            return None

    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Return the raw row for a job across all users (JSON cols are strings)."""
        if not self.is_configured():
            return None
        try:
            row, _ = self._execute(
                "SELECT * FROM videos WHERE job_id = %s",
                (job_id,),
                fetch="one",
            )
            return dict(row) if row else None
        except Exception:
            return None

    def get_active_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return jobs that are still pending/processing."""
        if not self.is_configured():
            return []
        try:
            rows, _ = self._execute(
                "SELECT * FROM videos WHERE status IN ('pending', 'processing') LIMIT %s",
                (limit,),
                fetch="all",
            )
            return [dict(r) for r in (rows or [])]
        except Exception as e:
            print(f"Error getting active jobs: {e}")
            return []


# Singleton instance
db_service = DBService()
