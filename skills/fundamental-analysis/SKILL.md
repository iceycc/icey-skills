---
name: fundamental-analysis
description: 股票基本面分析和选股工具集，支持获取财务指标（PE、PB、ROE、EPS、BPS、资产负债率等）、执行基本面选股策略（格雷厄姆 PB 选股、多因子选股）。用于分析公司基本面、筛选优质股票、执行价值投资策略。当需要获取股票财务指标、进行基本面选股、或执行价值投资策略时使用。
---

# 基本面分析工具集

提供股票基本面分析和选股功能。

## 功能

### 财务指标获取
- 获取单只股票的财务指标（PE、PB、ROE、EPS、BPS、市值等）
- 支持从 Tushare daily_basic 接口获取真实数据

### 选股策略

#### 格雷厄姆 PB 选股
- 筛选 PB < 1（破净）且 ROE > 5% 的股票
- 格雷厄姆"捡烟蒂"策略

#### 多因子基本面选股
- 连续多年 ROE > 15%
- 资产负债率 < 50%
- 净利润同比增长 > 0%
- 排除 ST 股和金融行业

## 使用方法

### 获取财务指标

```python
from scripts.get_financial_indicators import get_financial_indicators

# 获取单只股票的财务指标
indicators = get_financial_indicators(
    stock_code='600519.SH',
    stock_name='贵州茅台',
    data_file='data/600519_SH_daily.csv'
)
```

### 格雷厄姆 PB 选股

```python
from scripts.graham_pb_screener import run_screener

# 执行格雷厄姆 PB 选股
run_screener(
    pb_max=1.0,
    roe_min=5.0
)
```

### 多因子基本面选股

```python
from scripts.multi_factor_screener import run_screener

# 执行多因子选股
run_screener(
    roe_min=15,
    roe_consecutive_years=2,
    debt_to_assets_max=50,
    netprofit_yoy_min=0,
    exclude_finance=True,
    exclude_st=True
)
```

## 数据要求

需要以下数据文件（使用 stock-data-download skill 下载）：
- `data/stock_basic.csv` - 股票列表
- `data/daily_basic_latest.csv` - 估值数据
- `data/fina_indicator_pool.csv` - 财务指标

## 输出文件

- 格雷厄姆选股结果：`data/10-格雷厄姆PB选股_result.csv`
- 多因子选股结果：`data/11-综合基本面选股_result.csv`

## 注意事项

1. 需要先下载财务数据（使用 stock-data-download skill）
2. Tushare 需要设置环境变量 `TUSHARE_TOKEN`
3. 选股结果仅供参考，不构成投资建议
4. 金融行业（银行、保险、证券）的高杠杆是行业特性，选股时会自动排除
