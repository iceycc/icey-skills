---
name: stock-visualization
description: 股票数据可视化工具集，用于绘制 K 线图、成交量图、技术指标仪表盘等图表。支持绘制 K 线（阳线/阴线、影线）、成交量柱状图、多指标综合仪表盘（MA、RSI、ATR、成交量）。当需要可视化股票价格走势、技术指标、或制作多维度指标分析图表时使用。
---

# 股票数据可视化工具集

提供股票数据可视化的脚本和工具，支持 K 线图、成交量图、技术指标仪表盘等。

## 功能

### K 线图与成交量
- 绘制 K 线图（阳线/阴线、影线）
- 绘制成交量柱状图（红绿配色）
- 展示量价配合关系

### 指标仪表盘
- 多指标综合展示（趋势、震荡、能量、波动）
- 支持 MA、RSI、ATR、成交量等指标
- 四维指标仪表盘

## 使用方法

### K 线图与成交量

```python
from scripts.plot_kline_volume import plot_kline_volume

# 绘制 K 线图和成交量
plot_kline_volume(
    data_file='data/600519_SH_daily.csv',
    stock_name='贵州茅台',
    stock_code='600519.SH',
    show_days=60
)
```

### 指标仪表盘

```python
from scripts.plot_indicator_dashboard import plot_indicator_dashboard

# 绘制多指标仪表盘
plot_indicator_dashboard(
    data_file='data/600519_SH_daily.csv',
    stock_name='贵州茅台',
    stock_code='600519.SH',
    show_days=80,
    ma_period=20,
    rsi_period=14,
    atr_period=14
)
```

## 输出文件

- K 线图：`outputs/01_kline_volume_demo.png`
- 指标仪表盘：`outputs/9_{股票名称}指标仪表盘.png`

## 注意事项

1. 需要先下载股票数据（使用 stock-data-download skill）
2. 数据文件需包含 date, open, high, low, close, volume 列
3. 图表会自动保存到 outputs 目录
4. 支持中文显示，已配置中文字体
