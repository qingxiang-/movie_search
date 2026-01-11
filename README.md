# 电影 Magnet Link 搜索工具

使用 Playwright 无头浏览器搜索电影并提取 magnet link，支持 Qwen API 智能分析。

## 功能特性

- 多站点搜索（支持多个 BT 搜索站点）
- 无头浏览器自动化（Playwright + Chromium）
- Qwen API 智能分析推荐最佳资源
- 自动去重 magnet links

## 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

## 配置环境变量

```bash
# 复制模板文件
cp .env.example .env

# 编辑 .env 文件，填入真实的 API Key
```

环境变量配置：
```
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_MODEL=qwen-flash-2025-07-28
```

## 使用方法

```bash
python movie_search.py
```

然后输入要搜索的电影名称即可。

## 注意事项

- API Key 存储在 `.env` 文件中，已被 `.gitignore` 忽略，不会上传到 git
- 如果未配置 API Key，程序仍可运行基础搜索功能，只是没有 LLM 分析
- 搜索站点可能随时变化，需要根据实际情况调整
