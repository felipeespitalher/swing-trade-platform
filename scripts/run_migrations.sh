#!/bin/bash
# Migration helper script for Swing Trade Platform
# Usage: ./scripts/run_migrations.sh [command] [options]
# Commands: check, migrate, validate, info, clean (development only)

set -e

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-swing_trade}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres_password}"
MIGRATIONS_DIR="./backend/migrations"
FLYWAY_CMD="${FLYWAY_CMD:-flyway}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# FUNCTIONS
# ============================================================================

print_header() {
    echo -e "${GREEN}=====================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}=====================================${NC}"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Check if PostgreSQL is available
check_postgres_connection() {
    print_header "Checking PostgreSQL Connection"

    if ! command -v psql &> /dev/null; then
        print_error "psql not found. Install PostgreSQL client tools."
        exit 1
    fi

    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" &> /dev/null; then
        print_success "PostgreSQL connection successful"
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" | sed 's/^/  /'
    else
        print_error "Cannot connect to PostgreSQL at ${DB_HOST}:${DB_PORT}"
        echo "Attempting to create database..."
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;" || true
    fi
}

# Check TimescaleDB extension
check_timescaledb() {
    print_header "Checking TimescaleDB Extension"

    result=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT extname FROM pg_extension WHERE extname = 'timescaledb';" 2>/dev/null || echo "")

    if [[ "$result" == *"timescaledb"* ]]; then
        print_success "TimescaleDB extension is installed"
    else
        print_warning "TimescaleDB extension not found - will be created by migrations"
    fi
}

# Run Flyway migrate
run_migrate() {
    print_header "Running Flyway Migrations"

    check_postgres_connection
    check_timescaledb

    export FLYWAY_URL="jdbc:postgresql://${DB_HOST}:${DB_PORT}/${DB_NAME}"
    export FLYWAY_USER="$DB_USER"
    export FLYWAY_PASSWORD="$DB_PASSWORD"
    export FLYWAY_LOCATIONS="filesystem:${MIGRATIONS_DIR}"
    export FLYWAY_OUT_OF_ORDER="false"
    export FLYWAY_VALIDATE_ON_MIGRATE="true"

    if command -v flyway &> /dev/null; then
        echo "Running: flyway migrate"
        flyway migrate
    else
        print_error "Flyway CLI not found. Install with: npm install -g flyway-cli or brew install flyway"
        exit 1
    fi
}

# Check migration status
check_status() {
    print_header "Checking Migration Status"

    check_postgres_connection

    print_warning "Checking Flyway schema history..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
        "SELECT version, description, type, installed_on, execution_time, success FROM flyway_schema_history ORDER BY version;" 2>/dev/null || \
        print_warning "No migration history found (migrations not yet applied)"

    echo ""
    print_warning "Current tables in database:"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt" 2>/dev/null || \
        print_warning "Could not list tables"
}

# Validate migrations
validate_migrations() {
    print_header "Validating Migrations"

    if [ ! -d "$MIGRATIONS_DIR" ]; then
        print_error "Migrations directory not found: $MIGRATIONS_DIR"
        exit 1
    fi

    count=$(find "$MIGRATIONS_DIR" -name "V*.sql" | wc -l)
    print_success "Found $count migration files"

    echo ""
    echo "Migration files:"
    find "$MIGRATIONS_DIR" -name "V*.sql" -exec basename {} \; | sort | sed 's/^/  /'

    # Check for naming convention violations
    echo ""
    echo "Checking naming convention..."
    if find "$MIGRATIONS_DIR" -name "*.sql" ! -name "V[0-9]*__*.sql" ! -name "U[0-9]*__*.sql" -type f | grep -q .; then
        print_warning "Found files not matching Flyway naming convention"
        find "$MIGRATIONS_DIR" -name "*.sql" ! -name "V[0-9]*__*.sql" ! -name "U[0-9]*__*.sql" -type f | sed 's/^/  /'
    else
        print_success "All migration files follow Flyway naming convention"
    fi
}

# Get detailed info
show_info() {
    print_header "Migration Information"

    echo "Configuration:"
    echo "  Database Host: $DB_HOST"
    echo "  Database Port: $DB_PORT"
    echo "  Database Name: $DB_NAME"
    echo "  Database User: $DB_USER"
    echo "  Migrations Dir: $MIGRATIONS_DIR"

    echo ""
    validate_migrations

    echo ""
    check_postgres_connection
}

# Clean database (DEVELOPMENT ONLY - destructive!)
clean_database() {
    print_header "WARNING: CLEANING DATABASE"
    print_error "This will DROP all tables and reset migrations!"

    read -p "Are you sure? Type 'yes' to confirm: " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Cancelled."
        return
    fi

    print_warning "Dropping all tables..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
        DROP SCHEMA IF EXISTS public CASCADE;
        CREATE SCHEMA public;
        GRANT ALL ON SCHEMA public TO postgres;
EOF

    print_success "Database cleaned"
    print_warning "Next step: Run './scripts/run_migrations.sh migrate' to recreate schema"
}

# ============================================================================
# MAIN
# ============================================================================

usage() {
    cat << EOF
Usage: $0 [command] [options]

Commands:
  check       - Check migration status (default)
  migrate     - Run all pending migrations
  validate    - Validate migration files
  info        - Show configuration and migration info
  clean       - Clean database (DEVELOPMENT ONLY - destructive!)

Environment Variables:
  DB_HOST       - Database host (default: localhost)
  DB_PORT       - Database port (default: 5432)
  DB_NAME       - Database name (default: swing_trade)
  DB_USER       - Database user (default: postgres)
  DB_PASSWORD   - Database password (default: postgres_password)

Examples:
  ./scripts/run_migrations.sh check
  ./scripts/run_migrations.sh migrate
  DB_HOST=prod.example.com ./scripts/run_migrations.sh migrate
  ./scripts/run_migrations.sh validate

EOF
}

# Parse command
COMMAND="${1:-check}"

case "$COMMAND" in
    check)
        check_status
        ;;
    migrate)
        run_migrate
        ;;
    validate)
        validate_migrations
        ;;
    info)
        show_info
        ;;
    clean)
        clean_database
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        usage
        exit 1
        ;;
esac

print_success "Done"
