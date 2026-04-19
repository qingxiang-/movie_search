# Alpha158 因子分析 - LLM 智能分析功能

## 修改内容

### 1. `_get_top_stock_news` 函数 (alpha158_stock_screening.py:571)

**修改前**: 仅获取通用新闻摘要
**修改后**: 结合 Alpha 因子数据进行智能分析

```python
def _get_top_stock_news(ticker: str, api_key: str, use_azure: bool = False,
                        alpha_factors: Dict = None) -> str:
```

**新增功能**:
- 接收 `alpha_factors` 参数，包含该股票的所有因子数据
- 构建详细的因子数据摘要，传递给 LLM
- Prompt 要求 LLM 基于因子数据进行量化角度的解读
- 输出包含技术面分析、基本面分析和投资建议

### 2. `_analyze_top_stocks_with_llm` 函数 (alpha158_stock_screening.py:661)

**修改前**: 仅调用新闻获取，不传递因子数据
**修改后**: 提取并传递 Alpha 因子数据

```python
# 提取该股票的 alpha 因子
alpha_factors = {k: v for k, v in row.items() if k not in ['score']}

# Get analysis using LLM with alpha factors
analysis = _get_top_stock_news(ticker, api_key, use_azure=use_azure, alpha_factors=alpha_factors)
```

**返回值更新**:
- `'analysis'` 替代了 `'news_summary'`
- 新增 `'alpha_factors'` 字段

### 3. `_generate_enhanced_html` 函数 (alpha158_stock_screening.py:758)

**修改前**: 显示"新闻与资讯"
**修改后**: 显示"LLM 因子分析"

```python
<div class="news-summary">
    <strong>🤖 LLM 因子分析：</strong><br>
    {analysis.replace(chr(10), '<br>')}
</div>
```

### 4. 类型导入 (alpha158_stock_screening.py:13)

```python
from typing import Dict
```

## 分析流程

```
1. Alpha158 因子计算
   ↓
2. 综合评分排名
   ↓
3. 选择 TOP 5 股票
   ↓
4. 对每只股票:
   - 提取所有因子数据
   - 构建因子摘要 Prompt
   - 调用 LLM 进行分析
   ↓
5. 生成增强版 HTML 报告
   - TOP 20 推荐表格
   - TOP 5 深度分析（因子数据 + LLM 分析）
   ↓
6. 发送邮件
```

## LLM 分析 Prompt 结构

```
作为资深量化分析师，请对 {ticker} 股票进行深度分析。

## Alpha 因子数据
- 动量因子 (1M/3M/6M 收益，动量强度)
- 波动率因子 (年化波动率，趋势)
- 趋势因子 (均线系统信号，相对位置)
- 技术指标 (RSI, MACD, 均线)
- 估值因子 (行业，PE，相对 PE)

## 分析要求
1. 因子解读 (40%)
   - 动量持续性分析
   - 波动率风险提示
   - 趋势强度判断
   - 技术指标信号解读

2. 基本面分析 (30%)
   - 估值合理性分析
   - 行业对比和竞争地位
   - 公司特有优势和风险

3. 投资建议 (30%)
   - 明确的操作建议
   - 目标价位和止损位
   - 关键催化剂和风险因素

## 输出要求
- 用简洁的中文，避免套话
- 基于具体数据，不要泛泛而谈
- 结论要有可操作性
- 限制在 500 字以内
```

## 测试方法

### 1. 独立测试脚本

```bash
python test_alpha158_llm.py
```

使用模拟数据测试 LLM 分析功能，无需 pandas_ta 依赖。

### 2. 完整流程测试

```bash
python alpha158_stock_screening.py
```

需要安装以下依赖:
- pandas
- numpy
- scipy
- requests
- httpx
- openai
- python-dotenv
- pandas_ta (需要 ta-lib 系统库)

### 3. 环境变量配置

```bash
# .env 文件
DASHSCOPE_API_KEY=your_api_key_here
LLM_PROVIDER=qwen  # 或 azure
```

## 输出示例

### HTML 报告 - TOP 5 分析卡片

```
┌─────────────────────────────────────────────┐
│ AAPL                    得分：0.856         │
├─────────────────────────────────────────────┤
│ 6 月动量    夏普比率     波动率             │
│ +12.3%      1.25        22.5%               │
├─────────────────────────────────────────────┤
│ 🤖 LLM 因子分析:                             │
│ 从因子数据来看，AAPL 呈现以下特征：           │
│ 1. 动量方面：短期动能温和，1 月收益+5.2%...  │
│ 2. 波动率 22.5% 处于合理区间，趋势稳定...   │
│ 3. 均线多头排列，技术面偏多...              │
│ 4. 估值方面，PE 为 28.5，相对行业溢价 15%... │
│                                             │
│ 投资建议：持有，目标价$185，止损$165        │
└─────────────────────────────────────────────┘
```

## 优势

1. **数据驱动**: 基于实际计算的 Alpha 因子，不是空洞的分析
2. **量化视角**: LLM 从量化角度解读因子含义
3. **可操作性**: 给出具体的目标价和止损位
4. **个性化**: 每只股票的分析都基于其独特的因子数据
5. **全面性**: 涵盖技术面、基本面、投资建议

## 注意事项

1. 需要有效的 DashScope API Key
2. 如果没有实时新闻数据，LLM 会基于内部知识和因子数据进行分析
3. 分析结果仅供参考，不构成投资建议
