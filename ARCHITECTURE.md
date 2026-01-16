# 系统架构文档

## 项目概述

本项目包含两个基于 LLM 智能导航的搜索系统：

1. **电影 Magnet Link 搜索** - 使用 LLM 智能导航搜索电影 magnet 下载链接
2. **学术论文搜索** - 使用 LLM 自动规划、评估和推荐学术论文

## 核心设计理念

与传统硬编码爬虫不同，本系统使用 **LLM 作为决策核心**，动态规划搜索路径：

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  浏览器页面  │ ──> │  LLM 规划器  │ ──> │  动作执行器  │
│  (HTML)     │      │  (决策下一步)│      │  (操作浏览器)│
└─────────────┘      └─────────────┘      └─────────────┘
       ↑                                        │
       └──────────────── 迭代循环 ◄──────────────┘
```

### 工作流程

1. **初始搜索** - 在搜索引擎搜索目标内容
2. **页面分析** - 提取页面内容、链接列表、目标信息
3. **LLM 决策** - 将上下文信息发送给 LLM，规划下一步操作
4. **执行动作** - 执行 LLM 决策的操作（点击/搜索/翻页/返回等）
5. **迭代优化** - 重复步骤 2-4，直到达到目标或最大迭代次数
6. **智能推荐** - 使用 LLM 分析并推荐最佳结果

---

## 一、电影 Magnet Link 搜索系统

### 1.1 架构

```
movie_search.py
├── MovieSearcher (主类)
│   ├── plan_next_action()      # LLM 规划下一步操作
│   ├── execute_action()         # 执行浏览器操作
│   ├── extract_page_content()   # 提取页面核心内容（关键词优先）
│   ├── extract_links()          # 提取可点击链接
│   ├── extract_magnet_links()   # 提取 magnet links
│   ├── _goto_with_retry()       # 带重试机制的页面导航
│   └── analyze_with_llm()       # LLM 分析推荐最佳资源
└── main()                       # 入口函数
```

### 1.2 核心功能

#### LLM 智能导航

- **动态决策** - LLM 根据页面实时内容决定下一步操作
- **多动作支持** - 点击链接、搜索、翻页、返回、滚动、切换引擎、更改搜索词等
- **上下文感知** - 记住搜索历史和已发现的 magnet links
- **自适应策略** - 根据页面情况自动调整搜索策略

#### 搜索引擎

支持以下搜索引擎（优先级从高到低）：

| 引擎 | URL | 特点 |
|------|-----|------|
| DuckDuckGo | `https://duckduckgo.com/?q=` | 对 torrent/magnet 搜索友好 |
| Brave Search | `https://search.brave.com/search?q=` | 隐私友好，搜索结果质量高 |
| Bing | `https://www.bing.com/search?q=` | 备用引擎 |

#### LLM 支持的操作

| 操作 | 说明 | 参数 |
|------|------|------|
| `click_link` | 点击页面中的某个链接 | `link_index` (链接索引) |
| `search` | 在搜索引擎搜索新关键词 | `query`, `engine_index` |
| `switch_engine` | 切换到其他搜索引擎 | `engine_index` |
| `scroll` | 向下滚动页面查看更多内容 | 无 |
| `back` | 返回上一页 | 无 |
| `next_page` | 翻到下一页 | 无 |
| `change_query` | 更改搜索词重新搜索 | `query` (新搜索词) |
| `extract_magnets` | 提取 magnet links 并完成 | 无 |
| `stop` | 停止搜索 | 无 |

### 1.3 配置参数

```python
searcher = MovieSearcher(
    max_iterations=15,    # 最大迭代次数
    min_magnets=5,        # 最少 magnet links 数量
    max_retries=3         # 最大重试次数
)
```

### 1.4 Prompt 模板

#### 规划 Prompt (`get_planning_prompt`)

**输入上下文**：
- 当前 URL
- 当前搜索引擎索引
- 页面已发现 magnet links 数量
- 已完成迭代次数
- 累计发现 magnet links
- 页面内容摘要（关键词优先）
- 可点击的链接列表（前10个）
- 可用的搜索引擎列表

**输出格式**：
```json
{
    "action": "操作类型",
    "reason": "决策理由（简短说明）",
    "params": {
        "link_index": 1,
        "query": "新搜索词",
        "engine_index": 0
    }
}
```

#### 分析 Prompt (`get_analysis_prompt`)

**输入**：
- 电影名称
- Magnet links 列表（最多10个）

**输出格式**：
```json
{
    "best_match": "完整的 magnet link",
    "reason": "选择理由",
    "quality": "推测的视频质量",
    "confidence": "高/中/低"
}
```

### 1.5 内容提取策略

#### 关键词优先的内容提取

```python
def extract_page_content(self, html: str, max_length: int = 8000) -> str:
    """提取页面核心内容，优先保留包含关键词的段落"""
    keywords = ['magnet', '磁力', '下载', '种子', 'torrent',
                'bt', '电影', self.movie_name.lower()]

    # 计算每个段落的关键词权重
    # 按权重排序，优先保留相关内容
```

#### Magnet Link 提取

```python
def extract_magnet_links(self, page_text: str) -> List[str]:
    """从页面文本中提取所有 magnet links"""
    # 支持标准 40 位 SHA-1 哈希
    magnet_pattern = r'magnet:\?xt=urn:btih:[a-fA-F0-9]{40}(?:&[^\s<>"\'\']+)*'
```

### 1.6 使用方法

```bash
python movie_search.py
```

**交互流程**：
```
请输入要搜索的电影名称: 利刃出鞘3

[LLM 智能导航搜索...]

是否需要 LLM 推荐最佳下载源? (y/n): y
```

---

## 二、学术论文搜索系统

### 2.1 架构

```
paper_search.py (入口)
    │
    ├── agents/paper_agent.py (论文搜索 Agent)
    │       ├── generate_topic()              # LLM 生成搜索主题
    │       ├── refine_topic()                # LLM 优化主题
    │       ├── plan_query()                  # LLM 规划查询词
    │       ├── evaluate_paper()              # LLM 评估论文质量
    │       ├── decide_action()               # LLM 决定下一步操作
    │       └── autonomous_search()           # 完全自主的搜索流程
    │
    ├── utils/
    │   ├── candidate_pool.py                 # 候选池管理
    │   ├── deduplication.py                  # 去重管理
    │   └── email_sender.py                   # 邮件发送
    │
    └── prompts/paper_prompts.py              # Prompt 模板
```

### 2.2 核心功能

#### LLM 主题生成

**功能**：LLM 自主分析研究趋势，生成搜索主题

**输入**：
- 历史搜索主题（最近30天）
- 已发送论文统计
- 当前日期

**输出**：
```json
{
    "topic": "multimodal reasoning in large language models",
    "topic_zh": "大语言模型中的多模态推理",
    "reason": "多模态推理是当前LLM领域的热点...",
    "keywords": ["multimodal", "reasoning", "VLM"],
    "novelty_score": 8.5,
    "related_topics": ["vision-language models", ...]
}
```

**特点**：
- 基于 AI/LLM/RL/Agent 四大方向
- 参考 10 个热点领域
- 避免重复历史主题
- 关注交叉领域
- 平衡热门和新兴方向

#### LLM 查询规划

**优化策略**：
1. 初始阶段：通用术语，覆盖面广
2. 细化阶段：聚焦特定方向
3. 多角度：不同关键词组合
4. 权威来源：顶会/顶刊论文
5. 作者追踪：知名作者最新工作

#### LLM 论文评估

**评估标准**（0-10 分）：
- 相关性 30% - 与搜索主题的匹配度
- 创新性 25% - 是否提出新方法/新观点
- 影响力 20% - 引用数、作者声誉、单位知名度
- 时效性 15% - 是否解决当前热点问题
- 质量 10% - 研究严谨性、摘要清晰度

**决策逻辑**：
- 评分 >= 8.0：高质量，必须加入候选池
- 评分 6.0-8.0：中等质量，根据候选池状态决定
- 评分 < 6.0：低质量，跳过

#### 候选池管理

**特性**：
- 动态扩容：5-10 篇
- 质量控制：只接受 >= 7.0 分的论文
- 自动去重：基于 URL 和标题
- 智能排序：按重要性降序

#### 去重系统

**去重策略**：
1. URL 完全匹配 → 重复
2. 标题归一化后完全匹配 → 重复
3. 标题相似度 > 90% → 重复

**本地记录**：`sent_papers.json`

#### 邮件通知

**格式**：HTML 富文本

**内容包含**：
- 论文标题、作者、单位
- 发表时间、引用数、来源
- 完整摘要
- 重要性评分
- LLM 生成的核心观点总结
- 关键方法、创新点、应用场景
- 论文链接和 PDF 下载

### 2.3 搜索引擎

支持以下搜索引擎：

| 引擎 | URL | 用途 |
|------|-----|------|
| Google Scholar | 学术论文搜索 | 权威来源 |
| arXiv | 预印本论文 | 最新研究 |
| Semantic Scholar | 学术论文 | AI/ML 领域 |
| Google | 通用搜索 | 补充来源 |

### 2.4 配置参数

```python
agent = PaperSearchAgent(
    max_iterations=30,       # 最大迭代次数
    min_papers=5,            # 最少论文数
    max_papers=10,           # 最多论文数
    min_quality_score=7.0,   # 最低质量分
    date_range_days=7,       # 最近一周
    max_retries=3            # 最大重试次数
)
```

### 2.5 使用方法

```bash
python paper_search.py
```

**交互流程**：
```
📚 自主学术论文搜索系统

🤖 正在分析研究趋势，生成搜索主题...

✨ LLM 选择主题: multimodal reasoning in large language models
   中文: 大语言模型中的多模态推理
   理由: 多模态推理是当前LLM领域的热点...
   新颖度: 8.5/10

[自动搜索、评估、总结...]

📧 邮件发送成功！

💡 LLM 建议下次搜索: tool-augmented language models
```

---

## 三、核心技术模块

### 3.1 核心模块 (`core/`)

#### BaseBrowserAgent

所有 Agent 的基类，提供基础浏览器操作功能：

```python
class BaseBrowserAgent:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    async def _goto_with_retry(self, page: Page, url: str, timeout: int = 15000) -> bool:
        """带重试机制的页面导航"""

    def extract_page_content(self, html: str, max_length: int = 8000) -> str:
        """提取页面核心内容"""

    def extract_links(self, html: str, base_url: str, max_links: int = 15) -> List[Dict]:
        """提取页面中的关键链接"""
```

#### LLMClient

LLM API 客户端，封装所有 LLM 调用：

```python
class LLMClient:
    async def call(self, messages: list, temperature: float = 0.7) -> dict:
        """调用 Qwen API"""

    def parse_json_response(self, content: str) -> dict:
        """解析 LLM 返回的 JSON"""
```

### 3.2 Prompts 模块 (`prompts/`)

#### 电影搜索 Prompts (`movie_prompts.py`)

- `get_planning_prompt()` - LLM 规划下一步操作
- `get_analysis_prompt()` - LLM 分析推荐最佳 magnet link

#### 论文搜索 Prompts (`paper_prompts.py`)

- `get_query_planning_prompt()` - LLM 规划搜索查询
- `get_decision_making_prompt()` - LLM 决策制定
- `get_summarization_prompt()` - LLM 论文总结
- `get_topic_generation_prompt()` - LLM 生成搜索主题
- `get_topic_refinement_prompt()` - LLM 优化主题

### 3.3 工具模块 (`utils/`)

#### CandidatePool

候选池管理：

```python
class CandidatePool:
    def __init__(self, min_size: int = 5, max_size: int = 10, min_score: float = 7.0):
        self.min_size = min_size
        self.max_size = max_size
        self.min_score = min_score

    def add(self, item: dict) -> bool:
        """添加候选项目"""

    def is_full(self) -> bool:
        """检查是否已满"""

    def get_sorted_items(self) -> List[dict]:
        """获取排序后的候选列表"""
```

#### DeduplicationManager

去重管理：

```python
class DeduplicationManager:
    def __init__(self, record_file: str = "sent_papers.json"):
        self.record_file = record_file
        self.records = self._load_records()

    def is_duplicate(self, paper: dict) -> bool:
        """检查是否重复"""

    def add_record(self, paper: dict, topic: str):
        """添加发送记录"""
```

#### EmailSender

邮件发送：

```python
class EmailSender:
    def __init__(self, config: dict):
        self.config = config

    def send_paper_email(self, papers: List[dict], topic: str) -> bool:
        """发送论文邮件"""
```

---

## 四、环境配置

### 4.1 环境变量

在 `.env` 文件中配置：

```bash
# Qwen API 配置（必需）
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_API_KEY=sk-your-api-key-here
DASHSCOPE_MODEL=qwen-flash-2025-07-28

# 邮件配置（可选，论文搜索使用）
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
RECEIVER_EMAIL=receiver@example.com
```

### 4.2 依赖项

```
playwright==1.35.0        # 无头浏览器自动化
httpx>=0.24.0             # 异步 HTTP 客户端
python-dotenv>=0.19.0     # 环境变量管理
beautifulsoup4>=4.12.0    # HTML 解析
pytest>=7.0.0             # 测试框架
pytest-asyncio>=0.21.0    # 异步测试支持
```

### 4.3 安装

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

---

## 五、测试

### 5.1 运行单元测试

```bash
# 方式 1: 直接运行测试脚本
python test_movie_search.py

# 方式 2: 使用 pytest（推荐）
pytest test_movie_search.py -v
```

### 5.2 测试覆盖

测试包含以下内容：

- ✅ **搜索引擎配置测试** - 验证搜索引擎配置正确
- ✅ **搜索引擎调用测试** - 实际测试每个搜索引擎的页面加载
- ✅ **搜索引擎切换测试** - 验证 LLM 可以切换搜索引擎
- ✅ **重试机制测试** - 验证网络失败时的重试逻辑
- ✅ **Magnet 提取测试** - 验证正则表达式正确提取 magnet 链接
- ✅ **页面内容提取测试** - 验证关键词优先的内容提取策略
- ✅ **参数化配置测试** - 验证自定义参数生效

---

## 六、技术亮点

### 6.1 完全 LLM 驱动

- **电影搜索**：LLM 决定点击哪个链接、何时翻页、是否切换引擎
- **论文搜索**：LLM 自动生成主题、规划查询、评估质量

### 6.2 智能内容提取

- **关键词优先**：优先保留包含关键词的段落
- **动态权重**：根据关键词出现频率排序内容
- **去重过滤**：自动去除脚本、样式、广告

### 6.3 健壮性设计

- **重试机制**：网络失败自动重试
- **异常恢复**：LLM 失败时使用默认策略
- **资源管理**：确保浏览器资源正确释放

### 6.4 可扩展性

- **模块化设计**：核心、Agent、Prompts、Utils 分离
- **配置化**：搜索引擎、参数都支持自定义
- **Prompt 管理**：集中管理所有 Prompt 模板

---

## 七、文件结构

```
movie_search/
├── movie_search.py                 # 电影搜索入口
├── paper_search.py                 # 论文搜索入口
├── test_movie_search.py            # 单元测试
│
├── core/                           # 核心模块
│   ├── __init__.py
│   ├── base_agent.py              # Agent 基类
│   ├── llm_client.py              # LLM 客户端
│   └── browser_utils.py           # 浏览器工具
│
├── agents/                         # Agent 实现
│   ├── __init__.py
│   └── paper_agent.py             # 论文搜索 Agent
│
├── prompts/                        # Prompt 模板
│   ├── __init__.py
│   ├── movie_prompts.py           # 电影搜索 Prompts
│   └── paper_prompts.py           # 论文搜索 Prompts
│
├── utils/                          # 工具模块
│   ├── __init__.py
│   ├── candidate_pool.py          # 候选池管理
│   ├── deduplication.py           # 去重管理
│   └── email_sender.py            # 邮件发送
│
├── requirements.txt                # 依赖项
├── .env.example                    # 环境变量模板
├── .env                            # 环境变量配置（不提交）
├── README.md                       # 用户文档
└── ARCHITECTURE.md                 # 架构文档（本文件）
```

---

## 八、注意事项

### 8.1 API Key 安全

- `.env` 文件已被 `.gitignore` 忽略
- 不要将 API Key 提交到 Git 仓库
- 使用环境变量或密钥管理服务

### 8.2 网络环境

- 需要能访问搜索引擎和目标网站
- 如果网络受限，可能需要配置代理

### 8.3 资源消耗

- 每次搜索会进行多次 LLM API 调用
- 建议使用经济模型（如 Qwen Flash）
- 注意 API 调用额度

### 8.4 法律合规

- 本工具仅供学习和研究使用
- 请遵守当地法律法规，尊重版权
- 不要用于商业用途

---

## 九、开发计划

### Phase 1: 核心功能 ✅

- [x] LLM 驱动的浏览器自动化框架
- [x] 电影 magnet link 搜索
- [x] 论文搜索系统
- [x] Prompt 模块化

### Phase 2: 增强功能 ✅

- [x] 多搜索引擎支持
- [x] 重试机制
- [x] 智能内容提取
- [x] 自主主题生成
- [x] 单元测试

### Phase 3: 优化和扩展

- [ ] 添加更多搜索引擎（Google、DuckDuckGo）
- [ ] 支持代理配置
- [ ] 添加搜索历史记录
- [ ] 实现 GUI 界面
- [ ] 支持批量搜索
- [ ] 性能优化（并行处理）

---

## License

MIT License
