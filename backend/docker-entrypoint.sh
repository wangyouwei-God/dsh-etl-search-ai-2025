#!/bin/bash
# =====================================
# Docker Entrypoint Script
# =====================================
# This script performs automatic health checks and initializes
# the application before starting the main service.

set -e

echo "========================================"
echo "Dataset Search and Discovery - Startup"
echo "========================================"

# Check if database exists and has data
check_database() {
    if [ -f "/app/datasets.db" ]; then
        # Check if database has records
        COUNT=$(sqlite3 /app/datasets.db "SELECT COUNT(*) FROM datasets" 2>/dev/null || echo "0")
        if [ "$COUNT" -gt "0" ]; then
            echo "[OK] Database found with $COUNT datasets"
            return 0
        fi
    fi
    echo "[WARN] Database not found or empty"
    return 1
}

# Check if vector database exists and has data
check_vector_db() {
    if [ -d "/app/chroma_db" ] && [ "$(ls -A /app/chroma_db 2>/dev/null)" ]; then
        echo "[OK] Vector database found"
        return 0
    fi
    echo "[WARN] Vector database not found"
    return 1
}

# Main startup checks
echo ""
echo "Running startup checks..."
echo "----------------------------------------"

DB_OK=true
VECTOR_OK=true

check_database || DB_OK=false
check_vector_db || VECTOR_OK=false

echo "----------------------------------------"

if [ "$DB_OK" = true ] && [ "$VECTOR_OK" = true ]; then
    echo "[OK] All checks passed - starting server"
else
    echo ""
    echo "[INFO] Pre-seeded data not found."
    echo "[INFO] The system will start but some features may be limited."
    echo "[INFO] To populate data, run the ETL pipeline:"
    echo "       python src/scripts/batch_etl_runner.py /app/data/metadata-file-identifiers.txt"
    echo ""
fi

echo ""
echo "Starting FastAPI server..."
echo "========================================"

# Execute the main command
exec "$@"
