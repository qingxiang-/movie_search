# 大麦网演出搜索工具

基于 Playwright (headed 模式) + Azure GPT Vision Agent 的智能大麦网演出搜索工具。

## 功能特点

- ✅ **Playwright Headed 模式**: 使用真实浏览器，非 headless
- 🤖 **Azure GPT Vision Agent**: 智能识别页面元素和控件
- 🔐 **智能验证码处理**: GPT 决策 + 自动拖拽/点击
- 🎭 **多类别搜索**: 演唱会、话剧、歌剧、livehouse
- 📊 **结果汇总**: JSON 格式保存，终端美化输出

## 系统要求

- Python 3.7+
- Azure OpenAI API Key (支持 GPT-4 Vision)
- 网络连接

## 快速开始

### 1. 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置 Azure OpenAI：

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_azure_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.cognitiveservices.azure.com/
AZURE_OPENAI_API_VERSION=2025-04-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 3. 运行搜索

#### 使用脚本（推荐）

```bash
chmod +x run_damai_search.sh
./run_damai_search.sh
```

#### 直接运行

```bash
# 搜索所有类别
python damai_search.py

# 搜索指定类别
python damai_search.py --categories 演唱会,话剧

# 使用 headless 模式（不推荐，可能影响验证码处理）
python damai_search.py --headless
```

## 工作原理

### 1. 智能页面分析

```
截图 → GPT Vision 分析 → 识别元素 → 决策操作
```

- 自动截取页面截图
- 提取可交互元素（按钮、输入框、链接等）
- GPT Vision 分析页面结构和元素属性
- 返回 JSON 格式的操作指令

### 2. 验证码处理

#### 滑块验证码
```python
{
  "action": "drag",
  "target": {"coordinates": {"x": 100, "y": 200}},
  "value": 300,  # 拖拽距离
  "reasoning": "识别到滑块验证码，需要向右拖拽300px"
}
```

#### 点选验证码
```python
{
  "action": "captcha_click",
  "value": [
    {"x": 150, "y": 200},
    {"x": 300, "y": 250}
  ],
  "reasoning": "点击所有包含猫的图片"
}
```

### 3. 人类化操作

- **拖拽轨迹**: 贝塞尔曲线 + 随机抖动
- **点击延迟**: 随机间隔 0.3-0.6 秒
- **输入速度**: 模拟真实打字速度
- **滚动行为**: 平滑滚动 + 随机停顿

## 输出格式

### 终端输出

```
🎭 大麦网演出搜索结果
==========================================

📍 演唱会 (共 50 场)
--------------------
1. 周杰伦演唱会 2026
   📅 2026-03-15 | 📍 北京鸟巢 | 💰 380-1280元
   🔗 https://detail.damai.cn/item.htm?id=xxx

2. 五月天演唱会
   📅 2026-04-20 | 📍 上海体育场 | 💰 480-1580元
   🔗 https://detail.damai.cn/item.htm?id=yyy
```

### JSON 文件

自动保存到 `damai_results_YYYYMMDD_HHMMSS.json`:

```json
{
  "演唱会": {
    "events": [
      {
        "title": "周杰伦演唱会 2026",
        "date": "2026-03-15",
        "venue": "北京鸟巢",
        "price_range": "380-1280元",
        "status": "在售",
        "url": "https://detail.damai.cn/item.htm?id=xxx",
        "image": "https://img.damai.cn/xxx.jpg"
      }
    ],
    "total_count": 50,
    "search_time": "2026-01-23 18:19:00"
  }
}
```

## 架构设计

详细设计文档请参考: [`DAMAI_SEARCH_PLAN.md`](./DAMAI_SEARCH_PLAN.md)

## 注意事项

### 1. Azure OpenAI 成本

- GPT-4 Vision API 调用成本较高
- 每次搜索约调用 10-20 次 API
- 建议设置 Azure 消费限额

### 2. 反爬虫策略

- 使用 headed 模式降低检测风险
- 添加随机延迟和人类化操作
- 避免频繁请求，建议间隔 2-5 秒

### 3. 验证码处理

- GPT Vision 识别率约 80-90%
- 复杂验证码可能需要多次重试
- 建议人工监控首次运行

### 4. 网络环境

- 需要稳定的网络连接
- 建议使用国内网络访问大麦网
- Azure OpenAI 需要国际网络

## 故障排查

### 问题 1: Azure OpenAI 连接失败

```
❌ GPT 分析失败: Connection error
```

**解决方案**:
- 检查 `.env` 中的 API Key 和 Endpoint
- 确认 Azure OpenAI 服务状态
- 检查网络连接

### 问题 2: Playwright 浏览器未安装

```
❌ Executable doesn't exist at ...
```

**解决方案**:
```bash
python -m playwright install chromium
```

### 问题 3: 验证码处理失败

```
❌ 验证码处理失败: ...
```

**解决方案**:
- 使用 headed 模式观察验证码类型
- 手动完成验证码后继续运行
- 调整 GPT prompt 优化识别

### 问题 4: 页面元素定位失败

```
⚠️  无法定位点击目标
```

**解决方案**:
- 大麦网页面结构可能更新
- 检查页面截图分析 GPT 决策
- 更新元素选择器

## 开发计划

- [ ] 添加代理池支持
- [ ] 实现分布式爬取
- [ ] 添加数据库存储
- [ ] 实现增量更新
- [ ] 添加邮件/微信通知
- [ ] 优化 GPT Vision 调用频率
- [ ] 添加更多演出类别

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请提交 GitHub Issue。
