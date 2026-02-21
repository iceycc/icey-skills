---
name: technical-indicators
description: 股票技术指标计算和交易信号生成工具集，支持 MA（移动平均线）、MACD（指数平滑移动平均线）、RSI（相对强弱指标）、ATR（平均真实波幅）等常用技术指标的计算和可视化。用于计算技术指标、识别交易信号（金叉/死叉）、评估超买超卖状态、计算波动率和止损位。当需要分析股票技术面、生成交易信号、或进行技术指标分析时使用。
---

# 技术指标计算工具集

提供常用技术指标的计算和交易信号生成功能。

## 支持的指标

### MA (移动平均线)
- 计算短期和长期移动平均线
- 识别金叉（买入信号）和死叉（卖出信号）
- 脚本：`scripts/calc_ma_signals.py`

### MACD (指数平滑移动平均线)
- 计算 DIF、DEA、MACD 柱
- 识别金叉/死叉和背驰信号
- 脚本：`scripts/calc_macd_signals.py`

### RSI (相对强弱指标)
- 计算 RSI 值（0-100）
- 识别超买（RSI>80）和超卖（RSI<20）区域
- 脚本：`scripts/calc_rsi.py`

### ATR (平均真实波幅)
- 计算真实波幅和 ATR
- 用于止损位计算（2*ATR）
- 脚本：`scripts/calc_atr.py`

## 使用方法

### MA 交易信号

```python
from scripts.calc_ma_signals import calc_ma_signals

# 计算 MA 金叉死叉信号
signals = calc_ma_signals(
    data_file='data/600519_SH_daily.csv',
    stock_name='贵州茅台',
    stock_code='600519.SH',
    ma_short=5,
    ma_long=20,
    show_days=120
)
```

### MACD 交易信号

```python
from scripts.calc_macd_signals import calc_macd_signals

# 计算 MACD 信号
signals = calc_macd_signals(
    data_file='data/600519_SH_daily.csv',
    stock_name='贵州茅台',
    stock_code='600519.SH',
    short_period=12,
    long_period=26,
    signal_period=9,
    show_days=150
)
```

### RSI 指标

```python
from scripts.calc_rsi import calc_rsi

# 计算 RSI 指标
rsi_data = calc_rsi(
    data_file='data/600519_SH_daily.csv',
    stock_name='贵州茅台',
    stock_code='600519.SH',
    rsi_period=14,
    show_days=120
)
```

### ATR 指标

```python
from scripts.calc_atr import calc_atr

# 计算 ATR 和止损位
atr_data = calc_atr(
    data_file='data/601899_SH_daily.csv',
    stock_name='紫金矿业',
    stock_code='601899.SH',
    atr_period=14,
    lookback_days=60
)
```

## 输出文件

- MA 信号图：`outputs/4-贵州茅台MA交易信号.png`
- MACD 信号图：`outputs/5-贵州茅台MACD交易信号.png`
- RSI 指标图：`outputs/7-贵州茅台RSI指标计算.png`

## 注意事项

1. 需要先下载股票数据（使用 stock-data-download skill）
2. 不同指标需要的数据列不同：
   - MA/MACD/RSI：需要 close
   - ATR：需要 high, low, close
3. 指标计算会自动处理数据不足的情况
4. 交易信号仅供参考，不构成投资建议
