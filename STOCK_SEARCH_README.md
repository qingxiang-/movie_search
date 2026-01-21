# 美股智能分析系统

基于 LLM 的美股投资分析工具，自动搜索最新资讯和行情，分析并推荐最有投资价值的股票。

## 功能特点

- 🌐 **Headless 浏览器**: 使用 Playwright 直接访问专业财经网站，获取实时数据
- 🎯 **智能浏览**: 自动访问 Yahoo Finance、Finviz、MarketWatch 等权威网站
- 📊 **多源数据**: 从热门榜单、涨幅榜、成交量排行等多个维度收集股票
- 🤖 **LLM 分析**: 使用 Azure OpenAI GPT-5.2 进行深度分析
- 📈 **多维评估**: 从市场趋势、技术面、基本面、催化剂、风险等多个维度评估
- 💡 **投资推荐**: 每次推荐 3 只最有价值的股票
- 📧 **邮件通知**: 自动生成精美的 HTML 邮件并发送

## 架构设计

模仿 `paper_search.py` 和 `movie_search.py` 的设计：

```
stock_search.py                 # 主程序入口
├── agents/stock_agent.py       # 股票分析 Agent
├── prompts/stock_prompts.py    # LLM 提示词
├── utils/email_sender.py       # 邮件发送（已扩展支持股票）
└── core/llm_client.py          # LLM 客户端（支持 Azure OpenAI）
```

## 使用方法

### 1. 确保环境配置正确

`.env` 文件中需要配置：

```bash
# LLM Provider
LLM_PROVIDER=azure

# Azure OpenAI 配置
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_API_VERSION=2025-04-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-5.2

# 代理配置（如需要）
HTTP_PROXY=http://127.0.0.1:7890

# 阿里云邮件配置
ALIYUN_ACCESS_KEY_ID=your_access_key_id
ALIYUN_ACCESS_KEY_SECRET=your_access_key_secret
```

### 2. 运行股票分析

```bash
# 激活 conda 环境
conda activate search

# 或使用完整路径
~/opt/anaconda3/envs/search/bin/python stock_search.py
```

### 3. 分析流程

程序会自动：

1. **智能浏览阶段**: 使用 Headless 浏览器直接访问专业财经网站
   - Yahoo Finance Trending（实时热门股票榜单）
   - Yahoo Finance Gainers（今日涨幅榜）
   - Yahoo Finance Most Active（成交量最活跃股票）
   - Finviz Screener（股票筛选器）
   - MarketWatch Market Data（全球市场数据）
   - Investing.com Top Stocks（热门股票）

2. **数据提取阶段**: 从网页表格和内容中提取股票信息
   - 股票代码（Symbol）
   - 价格和涨跌幅（如果可用）
   - 来源网站标记

3. **分析阶段**: 使用 LLM 进行深度分析
   - 市场整体环境
   - 个股技术面和基本面
   - 催化剂和风险评估
   - 投资价值评分

4. **推荐阶段**: 选出最有价值的 3 只股票

5. **发送阶段**: 生成 HTML 邮件并发送

## 输出示例

### 控制台输出

```
======================================================================
📈 美股智能分析系统
======================================================================

🔍 搜索策略:
   1. best US stocks today market
   2. top performing stocks now
   3. stocks with high volume today
   4. trending stocks after hours

🎯 目标: 找出今晚最有投资价值的 3 只美股
📊 分析维度: 市场趋势、技术面、基本面、催化剂、风险

🚀 开始分析...

======================================================================
📊 分析结果
======================================================================

📈 市场概览:
   今晚美股市场整体呈现震荡上行态势，科技股表现强劲...

🏆 今晚最值得关注的 3 只股票:

──────────────────────────────────────────────────────────────────────
🥇 Top 1: NVDA - NVIDIA Corporation
   推荐: 买入 | 评分: 9.2/10

   核心理由:
      • AI 芯片需求持续旺盛，市场份额稳固
      • 最新财报超预期，营收同比增长 120%
      • 技术面突破关键阻力位，动能强劲

   催化剂:
      • 新一代 GPU 即将发布
      • 与多家云服务商签订大单

   风险提示:
      ⚠️  估值偏高，短期可能面临回调压力
      ⚠️  地缘政治风险可能影响供应链

   分析: NVIDIA 作为 AI 时代的核心受益者，长期增长逻辑清晰...
```

### 邮件内容

邮件包含：
- 📊 市场概览
- 🥇 Top 3 股票推荐（每只包含）
  - 推荐操作（买入/持有/观望）
  - 投资评分
  - 核心理由
  - 催化剂
  - 风险提示
  - 详细分析
- 💡 投资策略
- ⚠️ 风险警告

### 保存文件

- `data/stock_analysis_YYYY-MM-DD.json` - 完整分析结果
- `data/email_stock_美股投资推荐_YYYY-MM-DD.html` - 邮件 HTML

## 核心组件说明

### StockAnalysisAgent

主要功能：
- `search_stocks()`: 搜索并收集股票信息（支持直接访问和搜索引擎两种模式）
- `intelligent_browse()`: 智能浏览策略，优先访问最有价值的财经网站
- `visit_direct_site()`: 直接访问专业财经网站获取数据
- `extract_stock_info()`: 从页面提取股票代码（增强版，支持表格和文本提取）
- `analyze_stocks()`: 使用 LLM 分析并推荐
- `plan_next_action()`: LLM 决策下一步操作
- `execute_action()`: 执行搜索、点击等操作

### 直接访问网站配置（推荐）

```python
DIRECT_SITES = [
    {
        "name": "Yahoo Finance Trending",
        "url": "https://finance.yahoo.com/trending-tickers",
        "type": "trending",
        "description": "实时热门股票榜单"
    },
    {
        "name": "Yahoo Finance Gainers",
        "url": "https://finance.yahoo.com/gainers",
        "type": "gainers",
        "description": "今日涨幅榜"
    },
    # ... 更多专业网站
]
```

### 搜索引擎配置（备选）

```python
SEARCH_ENGINES = [
    {"name": "Google Finance", "url": "..."},
    {"name": "Yahoo Finance", "url": "..."},
    {"name": "MarketWatch", "url": "..."},
    {"name": "Seeking Alpha", "url": "..."}
]
```

### Headless 浏览器的优势

✅ **数据准确性**: 直接从官方财经网站获取，避免搜索引擎过滤  
✅ **实时性强**: 访问实时榜单，数据最新  
✅ **结构化数据**: 从表格中提取，信息更完整（价格、涨跌幅等）  
✅ **可控性高**: 可以访问任何想要的网站，不受搜索引擎限制  
✅ **灵活性强**: 可以根据需要调整访问策略和网站列表

### LLM 分析维度

1. **市场趋势**: 当前市场环境和板块轮动
2. **技术面**: 股价走势、支撑位、阻力位
3. **基本面**: 公司业绩、行业地位、增长潜力
4. **催化剂**: 近期重大利好消息
5. **风险评估**: 潜在风险和下行空间
6. **投资价值**: 短期和中期投资价值

## 自定义配置

### 切换访问模式

编辑 `stock_search.py` 中的 `search_stocks()` 调用：

```python
# 模式1: 仅直接访问财经网站（推荐，默认）
result = await agent.search_stocks(
    use_direct_sites=True,      # 启用直接访问
    use_search_engines=False    # 禁用搜索引擎
)

# 模式2: 仅使用搜索引擎
result = await agent.search_stocks(
    keywords=["best stocks today", "top gainers"],
    use_direct_sites=False,     # 禁用直接访问
    use_search_engines=True     # 启用搜索引擎
)

# 模式3: 混合模式（先直接访问，不足时补充搜索）
result = await agent.search_stocks(
    keywords=["trending stocks"],
    use_direct_sites=True,      # 启用直接访问
    use_search_engines=True     # 启用搜索引擎作为补充
)
```

### 添加自定义财经网站

编辑 `agents/stock_agent.py` 中的 `DIRECT_SITES`:

```python
DIRECT_SITES = [
    # ... 现有网站
    {
        "name": "Your Custom Site",
        "url": "https://your-site.com/stocks",
        "type": "custom",
        "description": "自定义数据源"
    }
]
```

### 调整访问网站数量

```python
# 在 intelligent_browse() 中调整
direct_stocks = await self.intelligent_browse(page, max_sites=5)  # 访问5个网站
```

### 调整股票数量

```python
agent = StockAnalysisAgent(
    max_iterations=20,    # 最大搜索迭代次数
    min_stocks=3,         # 最少找到的股票数
    max_stocks=10,        # 最多找到的股票数
    max_retries=3,
    proxy=proxy
)
```

### 修改分析提示词

编辑 `prompts/stock_prompts.py` 中的 `get_analysis_prompt()` 函数。

## 注意事项

⚠️ **免责声明**: 
- 本工具生成的内容仅供参考，不构成投资建议
- 投资有风险，入市需谨慎
- 请根据自身风险承受能力做出投资决策

⚠️ **技术限制**:
- 搜索结果依赖于网页内容，可能不完整
- LLM 分析基于有限信息，可能存在偏差
- 实时行情数据可能有延迟

⚠️ **使用建议**:
- 建议在美股盘后运行，获取当日完整数据
- 结合其他专业工具和人工判断
- 定期检查邮件配置和 API 额度

## 与其他 Agent 的对比

| 特性 | Paper Search | Movie Search | Stock Search |
|------|-------------|--------------|--------------|
| 搜索目标 | 学术论文 | 电影资源 | 美股投资机会 |
| 数据源 | arXiv, Google Scholar | 搜索引擎 | 财经网站 |
| 分析维度 | 学术价值、创新性 | 资源质量 | 投资价值、风险 |
| 输出数量 | 3 篇论文 | 多个链接 | 3 只股票 |
| 邮件格式 | 学术风格 | - | 投资报告风格 |
| 去重机制 | ✅ | ❌ | ❌ |

## 未来改进方向

- [ ] 添加实时股价数据获取
- [ ] 集成技术指标计算（RSI, MACD 等）
- [ ] 支持更多数据源（Bloomberg, Reuters）
- [ ] 添加历史推荐追踪和回测
- [ ] 支持自定义股票池筛选
- [ ] 添加风险评分模型
- [ ] 支持多市场（A股、港股等）

## 故障排查

### 问题：搜索不到股票

- 检查代理配置是否正确
- 确认网络连接正常
- 尝试更换搜索关键词

### 问题：LLM 分析失败

- 检查 Azure OpenAI API Key 是否有效
- 确认 API 额度是否充足
- 查看错误日志获取详细信息

### 问题：邮件发送失败

- 检查阿里云 DirectMail 配置
- 确认 `email_config.yaml` 配置正确
- 验证发件人地址已通过验证

## 许可证

与主项目保持一致
