#!/bin/bash
# Alpha158 多因子选股系统 - 每日分析报告
cd "$(dirname "$0")"

# Ensure log directory exists
mkdir -p logs

# Define log file with date
LOG_FILE="logs/stock_analysis_$(date +%Y-%m-%d).log"

echo "=======================================================" >> "$LOG_FILE"
echo "🚀 Starting Alpha158 Stock Analysis at $(date)" >> "$LOG_FILE"
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

# Run the Alpha158 ranking method with Playwright news search
$HOME/miniconda3/bin/python alpha158_stock_screening.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

echo "" >> "$LOG_FILE"
if [ $EXIT_CODE -eq 0 ]; then
  echo "✅ Stock Analysis completed successfully at $(date)" >> "$LOG_FILE"
else
  echo "❌ Stock Analysis failed with exit code $EXIT_CODE at $(date)" >> "$LOG_FILE"
fi
echo "=======================================================" >> "$LOG_FILE"
