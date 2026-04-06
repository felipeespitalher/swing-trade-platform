"""
Run SQL migrations against the database.

Applies all V*.sql files in /app/migrations in version order.
Tracks applied migrations in a simple `schema_migrations` table.

Usage:
    python scripts/migrate.py
"""
import os
import re
import sys

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations")


def get_migration_version(filename: str) -> int:
    m = re.match(r"V(\d+)__", filename)
    return int(m.group(1)) if m else -1


def run_migrations():
    conn = psycopg2.connect(DATABASE_URL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Create migrations tracking table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            applied_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Get already applied versions
    cur.execute("SELECT version FROM schema_migrations")
    applied = {row[0] for row in cur.fetchall()}

    # Find and sort migration files
    files = [
        f for f in os.listdir(MIGRATIONS_DIR)
        if f.endswith(".sql") and get_migration_version(f) > 0
    ]
    files.sort(key=get_migration_version)

    applied_count = 0
    for filename in files:
        version = get_migration_version(filename)
        if version in applied:
            print(f"  skip  V{version} — already applied")
            continue

        filepath = os.path.join(MIGRATIONS_DIR, filename)
        sql = open(filepath, encoding="utf-8").read()

        print(f"  apply V{version} — {filename}")
        try:
            cur.execute(sql)
            cur.execute(
                "INSERT INTO schema_migrations (version, filename) VALUES (%s, %s)",
                (version, filename),
            )
            applied_count += 1
        except Exception as e:
            print(f"  ERROR applying {filename}: {e}")
            # Non-fatal: continue with remaining migrations
            conn.rollback()

    cur.close()
    conn.close()
    print(f"Migrations complete: {applied_count} applied, {len(applied)} already up to date")


if __name__ == "__main__":
    print("Running database migrations...")
    run_migrations()
