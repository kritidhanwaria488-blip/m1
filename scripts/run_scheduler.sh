#!/bin/bash
# Local Ingestion Pipeline Scheduler for Unix/Linux/macOS
# Runs all phases 4.0 -> 4.1 -> 4.2 -> 4.3 with logging

set -e  # Exit on error

echo "============================================"
echo "Local Ingestion Pipeline Scheduler"
echo "============================================"
echo ""

# Check if we're in the right directory
if [ ! -f "runtime/phase_4_scrape/__init__.py" ]; then
    echo "Error: Please run this script from the project root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Get current timestamp for default run ID
RUN_ID=$(date +"%Y%m%d-%H%M%S")
VERBOSE=""
CUSTOM_RUN_ID=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE="--verbose"
            shift
            ;;
        --run-id)
            CUSTOM_RUN_ID="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --run-id ID       Use custom run ID (default: auto-generated)"
            echo "  --verbose, -v     Enable verbose logging"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0"
            echo "  $0 --verbose"
            echo "  $0 --run-id 20240424-180000"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Use custom run ID if provided
if [ -n "$CUSTOM_RUN_ID" ]; then
    RUN_ID="$CUSTOM_RUN_ID"
fi

echo "Run ID: $RUN_ID"
echo "Log File: logs/scheduler_${RUN_ID}.log"
echo ""

# Create logs directory
mkdir -p logs

# Run the scheduler
echo "Starting pipeline..."
echo ""

python3 scripts/local_scheduler.py --run-id "$RUN_ID" $VERBOSE

# Check result
if [ $? -eq 0 ]; then
    echo ""
    echo "============================================"
    echo "Pipeline COMPLETED SUCCESSFULLY"
    echo "Log file: logs/scheduler_${RUN_ID}.log"
    echo "Results: logs/results_${RUN_ID}.json"
    echo "============================================"
    exit 0
else
    echo ""
    echo "============================================"
    echo "Pipeline FAILED"
    echo "Check log file: logs/scheduler_${RUN_ID}.log"
    echo "============================================"
    exit 1
fi
