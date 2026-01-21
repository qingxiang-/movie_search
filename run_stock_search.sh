#!/bin/bash

# Navigate to the script's directory
cd "$(dirname "$0")"

# Ensure log directory exists
mkdir -p logs

# Define log file with date
LOG_FILE="logs/stock_search_$(date +%Y-%m-%d).log"

echo "=======================================================" >> "$LOG_FILE"
echo "🚀 Starting Stock Search at $(date)" >> "$LOG_FILE"
echo "=======================================================" >> "$LOG_FILE"

# Load environment variables if .env exists
if [ -f .env ]; then
  # Safer way to load env vars, handling spaces/quotes
  set -a
  source .env
  set +a
fi

# Configure Proxy
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"

# Run the python script
# Assuming python3 is in the path or use /usr/bin/python3
/usr/bin/python3 stock_search.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

echo "" >> "$LOG_FILE"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Stock Search completed successfully at $(date)" >> "$LOG_FILE"
else
    echo "❌ Stock Search failed with exit code $EXIT_CODE at $(date)" >> "$LOG_FILE"
fi
echo "=======================================================" >> "$LOG_FILE"
