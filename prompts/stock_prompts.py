"""
Stock Analysis Prompts - LLM预测版
"""
from typing import Dict, List


def get_prediction_prompt(symbol: str, stock_data: Dict) -> str:
    """生成LLM预测提示词"""
    
    returns = stock_data.get('returns', {})
    ma = stock_data.get('ma', {})
    position = stock_data.get('position', {})
    tech = stock_data.get('technical', {})
    
    return f"""作为一位资深量化投资分析师，请基于以下数据对 {symbol} 进行深度分析，预测其未来6个月的收益表现。

## 📊 核心数据

**价格与历史收益:**
- 当前价格: ${stock_data['current_price']}
- 近1个月: {returns.get('1m', 0):+.1f}%
- 近3个月: {returns.get('3m', 0):+.1f}%
- 近6个月: {returns.get('6m', 'N/A')}
- 波动率: {stock_data['volatility']}%

**技术指标:**
- MA20: ${ma.get('ma20', 'N/A')} (当前位置: {position.get('vs_ma20', 0):+.1f}%)
- MA50: ${ma.get('ma50', 'N/A')} (当前位置: {position.get('vs_ma50', 0):+.1f}%)
- MA200: ${ma.get('ma200', 'N/A') if ma.get('ma200') else 'N/A'}
- RSI (14): {tech.get('rsi', 'N/A')} ({'超买' if tech.get('rsi', 0) > 70 else ('超卖' if tech.get('rsi', 0) < 30 else '中性')})
- 趋势判断: {tech.get('trend', 'N/A')}

---

## 🎯 预测任务

请基于以上数据，进行以下分析：

### 1. 趋势判断
- 当前处于什么阶段？(上升趋势/下降趋势/震荡整理/超跌反弹/见顶回落)
- 短期动能如何？(强势/中性/弱势)

### 2. 估值位置
- 相对均线位置如何？(高估/合理/低估)
- RSI提示什么信号？

### 3. 催化剂分析
- 有什么潜在利好因素？
- 有什么潜在利空因素？

### 4. 综合预测

请给出 **未来6个月** 的收益预测：

| 指标 | 数值 |
|-----|------|
| 预测收益率 | ? |
| 置信度 | ? |
| 风险等级 | ? |
| 操作建议 | ? |

---

## 📝 输出要求

请以 JSON 格式返回：

```json
{{
    "predicted_return": -10.5,
    "predicted_price": 150.00,
    "confidence": "high",
    "risk_level": "medium",
    "recommendation": "持有",
    "current_phase": "上升趋势整理",
    "momentum": "中性偏强",
    "reasoning": "综合分析：虽然短期RSI显示超买，但MA多头排列未破，趋势仍向上...",
    "key_factors": [
        "因素1: 支撑位在MA20附近",
        "因素2: 行业增长强劲",
        "因素3: 估值偏高有回调压力"
    ],
    "upside_factors": [
        "新产品发布预期",
        "市场份额提升"
    ],
    "downside_factors": [
        "宏观环境不确定性",
        "竞争加剧"
    ],
    "entry_price": 165.50,
    "stop_loss": 145.00,
    "target_price_6m": 185.00
}}
```

**字段说明：**
- `predicted_return`: 预测收益率 (百分比，如 -10.5 表示下跌10.5%)
- `predicted_price`: 预测6个月后的价格
- `confidence`: 置信度 (high/medium/low)
- `risk_level`: 风险等级 (high/medium/low)
- `recommendation`: 建议 (买入/持有/观望/减仓/卖出)
- `current_phase`: 当前趋势阶段
- `momentum`: 短期动能描述
- `reasoning`: 分析逻辑 (100-200字)
- `key_factors`: 关键影响因素 (3-5条)
- `upside_factors`: 上涨催化剂 (2-3条)
- `downside_factors`: 下跌风险 (2-3条)
- `entry_price`: 建议入场价 (可选)
- `stop_loss`: 止损价 (可选)
- `target_price_6m`: 6个月目标价 (可选)

---

## ⚠️ 重要提示

1. **基于数据推理**：所有结论必须基于给出的数据，不是空泛的"基本面良好"
2. **量化思维**：说"RSI=75超买"比说"技术指标偏空"更具体
3. **区间预测**：可以给出概率分布，如"70%概率上涨5-15%，30%概率下跌5-10%"
4. **风险提示**：必须说明预测的不确定性和主要风险

请直接返回JSON，不要其他内容。"""


def get_technical_analysis_prompt(symbol: str, data: Dict) -> str:
    """技术分析专用Prompt"""
    return f"""对 {symbol} 进行纯技术分析：

当前价格: ${data.get('current_price')}
MA20: ${data.get('ma', {}).get('ma20')}
MA50: ${data.get('ma', {}).get('ma50')}
RSI: {data.get('rsi')}
趋势: {data.get('trend')}

请分析：
1. 短期支撑/阻力位
2. 技术形态判断
3. 交易信号

返回JSON格式。"""


def get_fundamental_analysis_prompt(symbol: str, data: Dict) -> str:
    """基本面分析专用Prompt"""
    return f"""对 {symbol} 进行基本面分析：

历史收益: 1M={data.get('returns', {}).get('1m')}%, 3M={data.get('returns', {}).get('3m')}%
波动率: {data.get('volatility')}

请分析：
1. 财报/业绩预期
2. 行业地位
3. 估值合理性

返回JSON格式。"""


def get_consensus_prediction_prompt(analysis: Dict) -> str:
    """综合预测Prompt"""
    return f"""综合以下分析，给出最终预测：

技术面: {analysis.get('technical', {})}
基本面: {analysis.get('fundamental', {})}

请给出最终预测结论。"""
