#!/bin/bash

# 大麦网演出搜索工具运行脚本

echo "🎭 大麦网演出搜索工具"
echo "================================"

# 使用当前环境的 Python（优先使用 conda 环境）
PYTHON_CMD="python3"
if [ -n "$CONDA_PREFIX" ]; then
    PYTHON_CMD="$CONDA_PREFIX/bin/python"
    echo "✓ 使用 Conda 环境: $CONDA_DEFAULT_ENV"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在，请先配置环境变量"
    echo "   参考 .env.example 创建 .env 文件"
    exit 1
fi

# 检查 Azure OpenAI 配置
if ! grep -q "AZURE_OPENAI_API_KEY" .env || grep -q "your_azure_api_key_here" .env; then
    echo "⚠️  请在 .env 文件中配置 Azure OpenAI API Key"
    exit 1
fi

# 安装依赖
echo "📦 检查依赖..."
$PYTHON_CMD -m pip install -r requirements.txt -q

# 安装 Playwright 浏览器
echo "🌐 检查 Playwright 浏览器..."
$PYTHON_CMD -m playwright install chromium

# 运行搜索
echo ""
echo "🚀 启动搜索..."
echo ""

# 默认搜索所有类别
if [ $# -eq 0 ]; then
    $PYTHON_CMD damai_search.py
else
    # 支持命令行参数
    $PYTHON_CMD damai_search.py "$@"
fi

echo ""
echo "✅ 完成！"
