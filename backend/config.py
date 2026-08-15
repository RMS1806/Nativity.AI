"""
Configuration management for Nativity.ai
Loads environment variables for API keys and service settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env from the first location that exists ─────────────────────────────
_config_dir = Path(__file__).resolve().parent

for _env_path in [
    _config_dir / ".env",
    _config_dir.parent / ".env",
    Path.cwd() / ".env",
]:
    if _env_path.exists():
        load_dotenv(dotenv_path=str(_env_path), override=True)
        break
else:
    load_dotenv()  # fallback: read from CWD / process env


class Settings:
    """Application settings loaded from environment variables."""

    # ── Google Gemini ─────────────────────────────────────────────────────────
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    # ── Cloudflare R2 (S3-compatible storage) ─────────────────────────────────
    R2_ACCOUNT_ID:       str = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID:    str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET_NAME:      str = os.getenv("R2_BUCKET_NAME", "")
    R2_PUBLIC_URL:       str = os.getenv("R2_PUBLIC_URL", "")  # e.g. https://pub-xxx.r2.dev

    # ── PostgreSQL (Supabase free tier) ───────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # ── Redis + Celery (Upstash free tier) ────────────────────────────────────
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ── Clerk Authentication ──────────────────────────────────────────────────
    CLERK_ISSUER_URL: str = os.getenv("CLERK_ISSUER_URL", "")

    # ── Application ───────────────────────────────────────────────────────────
    UPLOAD_DIR:       str = os.getenv("UPLOAD_DIR", "./uploads")
    OUTPUT_DIR:       str = os.getenv("OUTPUT_DIR", "./outputs")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "500"))

    SUPPORTED_LANGUAGES: list = ["hindi", "tamil", "bengali", "telugu", "marathi"]

    def validate(self) -> dict:
        """Validate that required settings are configured."""
        issues = []
        if not self.GOOGLE_API_KEY:
            issues.append("GOOGLE_API_KEY is not set")
        if not self.R2_ACCOUNT_ID:
            issues.append("R2_ACCOUNT_ID is not set")
        if not self.R2_ACCESS_KEY_ID:
            issues.append("R2_ACCESS_KEY_ID is not set")
        if not self.R2_BUCKET_NAME:
            issues.append("R2_BUCKET_NAME is not set")
        if not self.DATABASE_URL:
            issues.append("DATABASE_URL is not set (Supabase PostgreSQL)")
        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }


settings = Settings()
