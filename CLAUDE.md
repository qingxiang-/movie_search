# CLAUDE.md - 智能搜索与分析系统项目管理指南

## 项目概览

这是一个基于LLM（大语言模型）驱动的智能搜索与分析系统集合，包含多个专业领域的搜索工具。项目采用模块化架构，使用Playwright进行浏览器自动化，结合LLM进行智能决策和分析。

## 项目详细信息

### 1. 智能搜索系统架构

**项目类型**: LLM驱动的智能搜索与分析系统
**技术栈**: Python、Playwright、LLM API（Azure OpenAI、Qwen）、FastAPI
**核心架构**:
- LLM规划器：分析页面内容，决策下一步操作
- 动作执行器：执行浏览器操作（点击、搜索、翻页等）
- 迭代循环：持续优化搜索策略直到达到目标

### 2. 主要功能模块

#### 2.1 电影搜索系统 (`movie_search.py`)

**功能**: LLM驱动的电影magnet链接搜索
**特点**:
- 智能导航：LLM决定点击链接、切换引擎、翻页策略
- 多搜索引擎：DuckDuckGo、Brave、Bing
- 内容提取：关键词优先的页面内容分析
- Magnet识别：支持标准SHA-1哈希的magnet链接提取
- 智能推荐：LLM分析并推荐最佳下载源

**使用方法**:
```bash
python movie_search.py
```

#### 2.2 论文搜索系统 (`paper_search.py`)

**功能**: 自主学术论文搜索与推荐
**特点**:
- LLM主题生成：分析研究趋势，自动生成搜索主题
- 智能评估：LLM评估论文质量（相关性、创新性、影响力等）
- 候选池管理：动态维护高质量论文集合
- 去重系统：基于URL和标题的智能去重
- 邮件通知：自动发送HTML格式的论文推荐邮件

**使用方法**:
```bash
python paper_search.py
```

#### 2.3 股票搜索系统 (`stock_search.py`)

**功能**: 基于LLM的美股投资分析工具
**特点**:
- 智能浏览：直接访问Yahoo Finance、Finviz、MarketWatch等财经网站
- 多源数据：从热门榜单、涨幅榜、成交量排行收集股票信息
- LLM分析：从市场趋势、技术面、基本面、催化剂、风险等维度评估
- 投资推荐：每次推荐3只最有价值的股票
- 邮件通知：自动生成精美HTML报告并发送

**使用方法**:
```bash
python stock_search.py
```

#### 2.4 大麦网搜索系统 (`damai_search.py`)

**功能**: 智能演出搜索与验证码处理
**特点**:
- Playwright Headed模式：使用真实浏览器，降低检测风险
- GPT Vision Agent：智能识别页面元素和控件
- 智能验证码处理：GPT决策 + 自动拖拽/点击
- 多类别搜索：演唱会、话剧、歌剧、livehouse
- 结果汇总：JSON格式保存，终端美化输出

**使用方法**:
```bash
chmod +x run_damai_search.sh
./run_damai_search.sh
# 或直接运行
python damai_search.py --categories 演唱会,话剧
```

#### 2.5 Alpha158多因子选股系统

**功能**: 量化投资多因子选股模型
**特点**:
- Alpha158因子库：154个技术指标，分为5个批次
- 增强版因子库：新增55个因子，包括基本面、机器学习和高级组合因子
- 机器学习模型：RandomForest（57.5%准确率）、GradientBoosting
- 排名方法：Z-score标准化多因子评分，可配置因子权重
- 无未来泄漏：时间基的训练/测试分割
- MCP集成：支持Model Context Protocol，提供智能搜索和分析功能
- 智能缓存：数据获取和存储优化，支持增量更新
- 并行计算：优化的因子计算引擎，支持并行处理

**使用方法**:
```bash
pip install pandas pandas-ta scikit-learn xgboost
python ranking_method.py  # 使用传统API方法
python ranking_method.py --use-mcp  # 使用MCP增强模式
python ml_train_sklearn.py
```

**命令行选项**:
```bash
python ranking_method.py --help  # 查看所有选项
python ranking_method.py --use-mcp --period-days 60 --stock-pool my_stock_pool.csv
```

## 开发最佳实践

### 代码质量
- 使用pip管理Python依赖
- 保持代码结构清晰，模块化设计
- 核心、Agent、Prompts、Utils分离

### 安全性
- 敏感信息（API密钥）放在`.env`文件中
- 确保`.env`文件添加到`.gitignore`
- 定期更新依赖包以修复安全漏洞

### 文档
- 架构文档：`ARCHITECTURE.md`
- 项目说明：`README.md`、`STOCK_SEARCH_README.md`、`DAMAI_SEARCH_README.md`
- 因子分析：`ALPHA158_LLM_ANALYSIS.md`

## 环境配置

### 1. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装Playwright浏览器
python -m playwright install chromium
```

### 2. 配置环境变量

复制`.env.example`为`.env`并配置：

```bash
cp .env.example .env
```

**关键配置项**:
```env
# LLM Provider
LLM_PROVIDER=azure  # 或 qwen

# Azure OpenAI 配置
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_API_VERSION=2025-04-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Qwen API 配置
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_API_KEY=sk-your-api-key-here
DASHSCOPE_MODEL=qwen-flash-2025-07-28

# MCP (Model Context Protocol) 配置
MCP_BASE_URL=http://localhost:3000
MCP_API_KEY=your_mcp_api_key  # 可选，如需要认证

# 邮件配置
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
RECEIVER_EMAIL=receiver@example.com

# 代理配置（如需要）
HTTP_PROXY=http://127.0.0.1:7890
```

## 常用操作

### 运行项目

```bash
# 电影搜索
python movie_search.py

# 论文搜索
python paper_search.py

# 股票分析
python stock_search.py

# 大麦网搜索
python damai_search.py --categories 演唱会,话剧

# 选股系统（传统API方法）
python ranking_method.py

# 选股系统（MCP增强模式）
python ranking_method.py --use-mcp

# 选股系统（自定义参数）
python ranking_method.py --use-mcp --period-days 60 --stock-pool my_stock_pool.csv

# 机器学习训练
python ml_train_sklearn.py
```

### 使用脚本运行

```bash
# 运行股票分析
chmod +x run_stock_analysis.sh
./run_stock_analysis.sh

# 运行论文搜索
chmod +x run_paper_search.sh
./run_paper_search.sh

# 运行大麦网搜索
chmod +x run_damai_search.sh
./run_damai_search.sh
```

### 部署命令

```bash
rsync -avz --delete \
     --exclude node_modules \
     --exclude .next \
     --exclude .git \
     --exclude .env.local \
     --exclude __pycache__ \
     --exclude .pytest_cache \
     --exclude *.pyc \
     --exclude .DS_Store \
     ./ qingxiang@39.106.144.1:~/movie_search/
```

## 项目文件结构

```
movie_search/
├── core/                           # 核心模块
│   ├── base_agent.py              # Agent基类
│   ├── llm_client.py              # LLM客户端
│   ├── browser_utils.py           # 浏览器工具
│   └── mcp_client.py              # MCP（Model Context Protocol）客户端
├── agents/                         # Agent实现
│   ├── paper_agent.py             # 论文搜索Agent
│   └── stock_agent.py             # 股票分析Agent
├── prompts/                        # Prompt模板
│   ├── movie_prompts.py           # 电影搜索Prompts
│   ├── paper_prompts.py           # 论文搜索Prompts
│   └── stock_prompts.py           # 股票搜索Prompts
├── utils/                          # 工具模块
│   ├── candidate_pool.py          # 候选池管理
│   ├── deduplication.py           # 去重管理
│   ├── email_sender.py            # 邮件发送
│   ├── data_cache.py              # 智能数据缓存管理
│   └── incremental_updater.py     # 增量更新策略
├── data/                           # 数据存储
├── logs/                           # 日志文件
├── memory/                         # 记忆模块
├── tests/                          # 测试文件
├── movie_search.py                 # 电影搜索入口
├── paper_search.py                 # 论文搜索入口
├── stock_search.py                 # 股票搜索入口
├── damai_search.py                 # 大麦网搜索入口
├── alpha158.py                     # Alpha158因子库（基础版）
├── alpha158_enhanced.py            # Alpha158因子库（增强版）
├── alpha158_lite.py                # Alpha158因子库（轻量级）
├── ranking_method.py               # 选股策略
├── ml_train_sklearn.py             # 机器学习训练
├── ml_dataset_builder_v4.py        # 数据集构建
├── requirements.txt                # 依赖项
├── .env.example                    # 环境变量模板
├── .env                            # 环境变量配置
└── README.md                       # 用户文档
```

## 故障排除

### 常见问题

1. **Playwright浏览器未安装**:
   ```bash
   python -m playwright install chromium
   ```

2. **LLM连接失败**:
   - 检查API Key和Endpoint配置
   - 确认网络连接正常
   - 检查Azure OpenAI服务状态

3. **验证码处理失败**:
   - 使用headed模式观察验证码类型
   - 手动完成验证码后继续运行
   - 调整GPT prompt优化识别

4. **搜索结果不完整**:
   - 检查代理配置是否正确
   - 尝试更换搜索关键词
   - 调整访问网站数量

## 注意事项

### 免责声明
- 本工具生成的内容仅供参考，不构成投资建议
- 电影搜索功能仅供学习和研究使用，请遵守版权法
- 论文搜索结果基于有限信息，可能存在偏差

### 技术限制
- 搜索结果依赖于网页内容，可能不完整
- LLM分析基于有限信息，可能存在偏差
- 实时行情数据可能有延迟

### 使用建议
- 建议在美股盘后运行股票分析，获取当日完整数据
- 结合其他专业工具和人工判断
- 定期检查邮件配置和API额度
- 大麦网搜索建议使用国内网络

## 未来改进方向

1. **功能增强**
   - 添加实时股价数据获取
   - 支持更多数据源（Bloomberg、Reuters）
   - 添加历史推荐追踪和回测
   - 集成技术指标计算（RSI、MACD等）

2. **性能优化**
   - 并行搜索多个关键词
   - 优化LLM API调用频率

3. **用户体验**
   - 添加GUI界面
   - 支持批量搜索
   - 添加搜索历史记录
   - 可视化图表和报告生成

## 许可证

MIT License

---

**最后更新**: 2026-04-11
**版本**: v1.0