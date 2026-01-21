#!/bin/bash

# Navigate to the script's directory
cd "$(dirname "$0")"

# Ensure log directory exists
mkdir -p logs

# Define log file with date
LOG_FILE="logs/paper_search_$(date +%Y-%m-%d).log"

echo "=======================================================" >> "$LOG_FILE"
echo "🚀 Starting Paper Search at $(date)" >> "$LOG_FILE"
echo "=======================================================" >> "$LOG_FILE"

# Load environment variables if .env exists
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# Configure Proxy
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"

# Run the python script
# Using /usr/bin/python3 for consistency with stock search script on remote
/usr/bin/python3 paper_search.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

echo "" >> "$LOG_FILE"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Paper Search completed successfully at $(date)" >> "$LOG_FILE"
else
    echo "❌ Paper Search failed with exit code $EXIT_CODE at $(date)" >> "$LOG_FILE"
fi
echo "=======================================================" >> "$LOG_FILE"