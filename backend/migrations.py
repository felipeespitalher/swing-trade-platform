"""
Database migration runner for Swing Trade Platform.
Integrates Flyway-style migrations for PostgreSQL + TimescaleDB.

This module can be called:
1. At application startup (auto-migrate)
2. Manually via CLI command
3. In containers (init container pattern)

Usage:
    python migrations.py --check          # Check status
    python migrations.py --migrate        # Run pending migrations
    python migrations.py --validate       # Validate migration files
"""

import os
import sys
import psycopg2
import psycopg2.extras
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import hashlib
import argparse
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'swing_trade')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres_password')

MIGRATIONS_DIR = Path(__file__).parent / 'migrations'
MIGRATION_PATTERN = 'V*.sql'

# ============================================================================
# MIGRATION HISTORY TABLE
# ============================================================================

CREATE_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS flyway_schema_history (
  installed_rank SERIAL NOT NULL PRIMARY KEY,
  version INT,
  description VARCHAR(255) NOT NULL,
  type VARCHAR(20) NOT NULL,
  script VARCHAR(1000) NOT NULL,
  checksum INT,
  installed_by VARCHAR(100) NOT NULL,
  installed_on TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  execution_time INT NOT NULL,
  success BOOLEAN NOT NULL,
  UNIQUE(version)
);

CREATE INDEX IF NOT EXISTS flyway_schema_history_success
  ON flyway_schema_history(success);

COMMENT ON TABLE flyway_schema_history IS
  'Flyway schema history table - tracks all applied migrations';
"""

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

class MigrationRunner:
    """Handles database migration operations."""

    def __init__(self):
        """Initialize migration runner with database connection."""
        self.conn = None
        self.cursor = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                connection_factory=psycopg2.extras.RealDictConnection
            )
            self.cursor = self.conn.cursor()
            logger.info(f"Connected to PostgreSQL at {DB_HOST}:{DB_PORT}/{DB_NAME}")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from database")

    def execute(self, sql: str, commit: bool = True):
        """Execute SQL statement."""
        try:
            self.cursor.execute(sql)
            if commit:
                self.conn.commit()
            # Try to fetch results if available
            try:
                return self.cursor.fetchall()
            except psycopg2.ProgrammingError:
                # No results to fetch (e.g., CREATE TABLE, INSERT)
                return []
        except psycopg2.Error as e:
            self.conn.rollback()
            logger.error(f"SQL Error: {e}")
            raise

    def init_history_table(self):
        """Initialize migration history table if not exists."""
        logger.info("Initializing migration history table...")
        try:
            self.cursor.execute(CREATE_HISTORY_TABLE)
            self.conn.commit()
            logger.info("✓ Migration history table ready")
        except psycopg2.Error as e:
            self.conn.rollback()
            logger.error(f"SQL Error: {e}")
            raise

    def get_applied_migrations(self) -> Dict[int, Dict]:
        """Get all applied migrations."""
        self.init_history_table()
        result = self.execute("""
            SELECT version, description, script, checksum, installed_on, success
            FROM flyway_schema_history
            ORDER BY version;
        """, commit=False)
        return {row['version']: row for row in result}

    def record_migration(self, version: int, description: str, script: str,
                        checksum: int, execution_time: int, success: bool):
        """Record applied migration in history."""
        try:
            self.cursor.execute("""
                INSERT INTO flyway_schema_history
                (version, description, type, script, checksum, installed_by,
                 execution_time, success)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (version, description, "SQL", script, checksum, "python", execution_time, success))
            self.conn.commit()
            logger.info(f"✓ Recorded migration V{version}__{description}")
        except psycopg2.Error as e:
            self.conn.rollback()
            logger.error(f"Failed to record migration: {e}")
            raise

    def check_postgres_health(self) -> bool:
        """Check PostgreSQL connection and basic health."""
        try:
            result = self.execute(
                "SELECT version();",
                commit=False
            )
            version_info = result[0]['version'] if result else "Unknown"
            logger.info(f"PostgreSQL: {version_info[:60]}...")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False

    def check_timescaledb(self) -> bool:
        """Check if TimescaleDB extension is installed."""
        try:
            result = self.execute("""
                SELECT extname FROM pg_extension
                WHERE extname = 'timescaledb';
            """, commit=False)
            if result:
                logger.info("✓ TimescaleDB extension is installed")
                return True
            else:
                logger.warning("TimescaleDB extension not yet installed")
                return False
        except Exception as e:
            logger.warning(f"Could not check TimescaleDB: {e}")
            return False

    def get_pending_migrations(self) -> List[Tuple[int, str, Path]]:
        """Get all pending migrations not yet applied."""
        applied = self.get_applied_migrations()
        pending = []

        # Find all migration files
        migration_files = sorted(MIGRATIONS_DIR.glob(MIGRATION_PATTERN))

        for mig_file in migration_files:
            # Parse version from filename (V1__init_schema.sql -> 1)
            try:
                parts = mig_file.stem.split('__')
                version = int(parts[0][1:])  # Remove 'V' prefix
                description = parts[1] if len(parts) > 1 else ''

                if version not in applied:
                    pending.append((version, description, mig_file))
            except (ValueError, IndexError) as e:
                logger.warning(f"Invalid migration filename: {mig_file.name} ({e})")

        return pending

    def calculate_checksum(self, content: str) -> int:
        """Calculate checksum of SQL content."""
        return int(hashlib.md5(content.encode()).hexdigest(), 16) & 0x7FFFFFFF

# ============================================================================
# COMMANDS
# ============================================================================

def cmd_check(runner: MigrationRunner):
    """Check migration status."""
    logger.info("Checking migration status...")

    if not runner.check_postgres_health():
        logger.error("Cannot connect to database")
        return False

    runner.check_timescaledb()

    applied = runner.get_applied_migrations()
    if applied:
        logger.info(f"Applied migrations: {len(applied)}")
        for v, info in sorted(applied.items()):
            logger.info(f"  V{v:02d}: {info['description']} "
                       f"({info['installed_on']})")
    else:
        logger.info("No migrations applied yet")

    pending = runner.get_pending_migrations()
    if pending:
        logger.info(f"Pending migrations: {len(pending)}")
        for v, desc, path in pending:
            logger.info(f"  V{v:02d}__{desc}.sql")
    else:
        logger.info("✓ All migrations applied")

    return True


def cmd_validate(runner: MigrationRunner):
    """Validate migration files."""
    logger.info("Validating migrations...")

    if not MIGRATIONS_DIR.exists():
        logger.error(f"Migrations directory not found: {MIGRATIONS_DIR}")
        return False

    migration_files = list(MIGRATIONS_DIR.glob(MIGRATION_PATTERN))
    logger.info(f"Found {len(migration_files)} migration files")

    errors = False
    for mig_file in sorted(migration_files):
        try:
            # Validate filename
            parts = mig_file.stem.split('__')
            if len(parts) < 2:
                logger.error(f"Invalid format: {mig_file.name} "
                           "(must be V{N}__{description})")
                errors = True
                continue

            version_str = parts[0]
            if not version_str.startswith('V') or not version_str[1:].isdigit():
                logger.error(f"Invalid version: {mig_file.name} "
                           f"(must start with V followed by digits)")
                errors = True
                continue

            # Check file size
            size = mig_file.stat().st_size
            if size == 0:
                logger.error(f"Empty file: {mig_file.name}")
                errors = True
                continue

            logger.info(f"✓ {mig_file.name} ({size} bytes)")

        except Exception as e:
            logger.error(f"Error validating {mig_file.name}: {e}")
            errors = True

    return not errors


def cmd_migrate(runner: MigrationRunner):
    """Run pending migrations."""
    logger.info("Running migrations...")

    if not runner.check_postgres_health():
        logger.error("Cannot connect to database")
        return False

    runner.init_history_table()

    pending = runner.get_pending_migrations()
    if not pending:
        logger.info("✓ All migrations already applied")
        return True

    logger.info(f"Applying {len(pending)} migration(s)...")

    for version, description, mig_file in pending:
        logger.info(f"Applying V{version}__{description}...")

        try:
            # Read migration file
            with open(mig_file, 'r') as f:
                sql_content = f.read()

            # Calculate checksum
            checksum = runner.calculate_checksum(sql_content)

            # Execute migration
            start_time = datetime.now()
            runner.execute(sql_content)
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Record in history
            runner.record_migration(
                version=version,
                description=description,
                script=mig_file.name,
                checksum=checksum,
                execution_time=execution_time,
                success=True
            )

            logger.info(f"✓ V{version}__{description} "
                       f"({execution_time}ms)")

        except Exception as e:
            logger.error(f"✗ Migration V{version}__{description} failed: {e}")
            return False

    logger.info("✓ All migrations applied successfully")
    return True


def cmd_info(runner: MigrationRunner):
    """Show migration information."""
    logger.info("Migration Information")
    logger.info(f"Database: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    logger.info(f"Migrations Dir: {MIGRATIONS_DIR}")

    if runner.check_postgres_health():
        runner.check_timescaledb()
        cmd_check(runner)

    return True


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Database migration tool for Swing Trade Platform',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrations.py --check              # Check status
  python migrations.py --migrate            # Run pending migrations
  python migrations.py --validate           # Validate migration files
  python migrations.py --info               # Show configuration
        """
    )

    parser.add_argument('--check', action='store_true',
                       help='Check migration status (default)')
    parser.add_argument('--migrate', action='store_true',
                       help='Run pending migrations')
    parser.add_argument('--validate', action='store_true',
                       help='Validate migration files')
    parser.add_argument('--info', action='store_true',
                       help='Show configuration info')

    args = parser.parse_args()

    # Default to check if no command specified
    if not any([args.check, args.migrate, args.validate, args.info]):
        args.check = True

    try:
        with MigrationRunner() as runner:
            if args.check:
                success = cmd_check(runner)
            elif args.migrate:
                success = cmd_migrate(runner)
            elif args.validate:
                success = cmd_validate(runner)
            elif args.info:
                success = cmd_info(runner)

            return 0 if success else 1

    except KeyboardInterrupt:
        logger.info("Migration cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
