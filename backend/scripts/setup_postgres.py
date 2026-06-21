"""
PostgreSQL setup for Nativity.ai
Creates the `videos` table (and indexes) from schema.sql.

Usage:
    # DATABASE_URL must be set (in backend/.env or the shell)
    python scripts/setup_postgres.py

Tip: when running from your laptop against Render Postgres, use the EXTERNAL
Database URL (it needs SSL). The app itself should use the INTERNAL URL.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings  # noqa: E402

import psycopg2  # noqa: E402


def main():
    print("=" * 60)
    print("🚀 NATIVITY.AI POSTGRES SETUP")
    print("=" * 60)

    if not settings.DATABASE_URL:
        print("❌ DATABASE_URL not configured. Set it in backend/.env or the shell.")
        sys.exit(1)

    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        ddl = f.read()

    print(f"📄 Applying schema: {schema_path}")
    conn = psycopg2.connect(settings.DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
        # Confirm
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.videos')")
            exists = cur.fetchone()[0]
        print(f"✅ Table ready: {exists}")
    finally:
        conn.close()

    print("=" * 60)
    print("✅ Setup complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
