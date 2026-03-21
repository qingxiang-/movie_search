#!/bin/bash
# Weekly Keyword Update Script
# 每周运行一次，更新论文搜索关键词
# 建议在crontab中设置: 0 0 * * 0 /path/to/run_weekly_keyword_update.sh

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 创建日志目录
mkdir -p logs

# 设置日志文件
DATE=$(date +%Y-%m-%d)
LOG_FILE="logs/keyword_update_${DATE}.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "Weekly Keyword Update - $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# 加载环境变量
if [ -f .env ]; then
    echo "Loading .env file..." | tee -a "$LOG_FILE"
    export $(cat .env | grep -v '^#' | xargs)
fi

# 设置代理
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890

# 激活conda环境（如果需要）
if [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then
    source ~/miniconda3/etc/profile.d/conda.sh
    conda activate base
fi

# 运行关键词更新脚本
echo "Running keyword update..." | tee -a "$LOG_FILE"
python weekly_keyword_updater.py >> "$LOG_FILE" 2>&1

# 检查结果
if [ $? -eq 0 ]; then
    echo "✅ Keyword update completed successfully" | tee -a "$LOG_FILE"
else
    echo "❌ Keyword update failed" | tee -a "$LOG_FILE"
fi

echo "Log saved to: $LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"