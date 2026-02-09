# 因子计算失败问题分析

## 问题描述
远程服务器执行 Top 20 科技股因子计算时，132只股票全部失败，只显示"无有效数据"。

## 根本原因

### 1. pandas_ta 模块缺失
- 远程服务器没有安装 `pandas_ta` 模块
- 错误信息: `ModuleNotFoundError: No module named 'pandas_ta'`

### 2. Shim 兼容性问题
- 远程服务器有 `pandas_ta_shim.py` 作为 fallback
- 但 shim 的列名格式与 `alpha158.py` 期望的不完全匹配

**列名对比：**
| 指标 | alpha158.py 期望 | pandas_ta 返回 | shim 返回 |
|------|-----------------|-----------------|-----------|
| MACD | MACD, MACDs | MACD_12_26_9, MACDs_12_26_9 | MACD_12_26_9, MACDs_12_26_9 |
| BB | BBU_, BBM_, BBL_ | BBL_20_2.0, etc | BBL_20_2.0, etc |
| ADX | ADX_ | ADX_14 | ADX_14 |
| STOCH | STOCHk, STOCHd | STOCHk_14_3_3 | STOCHk_14_3_3 |

### 3. 异常被静默吞掉
`ranking_method.py:172-173`:
```python
except:
    return {}
```
所有异常被捕获后返回空字典，导致错误被隐藏。

## 解决方案

### 方案1: 安装 pandas_ta (推荐)
```bash
pip install pandas_ta
```

### 方案2: 修复 Shim 列名兼容
修改 `pandas_ta_shim.py` 中的返回值，使用与 pandas_ta 相同格式的列名。

### 方案3: 改进错误处理
在 `ranking_method.py` 中添加更详细的错误日志：
```python
except Exception as e:
    print(f"因子计算错误: {e}")
    import traceback
    traceback.print_exc()
    return {}
```

## 本地测试结果
使用100行数据测试：
- Batch1: 17个因子 ✓
- Batch2: 34个因子 ✓
- Batch3: 37个因子 ✓
- 总计: 88个因子

本地环境 pandas_ta 版本: 0.4.71b0

## 关键发现
1. MACD 需要至少 ~35 个数据点（slow=26 + signal=9）
2. 远程服务器缺少 pandas_ta 是直接原因
3. 之前的"5个成功"可能是因为数据不足导致的误判
