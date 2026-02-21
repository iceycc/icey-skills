---
name: stock-data-download
description: 股票数据下载工具集，支持从 QMT、Tushare、AkShare 下载日线、分钟、财务数据。股票代码、时间区间、输出目录等均通过用户 prompt 或脚本参数传入，脚本内无写死配置。当需要下载某只股票/某段时间的行情或财务数据、或准备选股分析所需基础数据时使用。
---

# 股票数据下载工具集

所有脚本均为**通用脚本**：股票代码、时间区间、输出目录等由**用户 prompt 或命令行/函数参数**传入，不在脚本内写死。调用时根据用户需求从对话中提取股票代码、日期范围等再调用对应脚本。

## 数据源与脚本一览

**日线区分：历史数据 vs 复权数据（两者并存，不合并）**

| 类型     | 数据源   | 脚本 | 说明 | 主要参数 |
|----------|----------|------|------|----------|
| 日线     | QMT      | `download_qmt_daily.py` | 日线 | `--stock-code` `--start-date` `--end-date` `--output-dir` |
| 日线-历史 | Tushare  | `download_tushare_daily.py` | **历史数据**（pro.daily，未复权） | `--stock-code` `--start-date` `--end-date` `--output-dir` |
| 日线-复权 | Tushare  | `download_tushare_daily_adj.py` | **复权日线**（ts.pro_bar 前复权/后复权） | `--stock-code` `--start-date` `--end-date` `--output-dir` `--adj`(qfq/hfq) |
| 日线     | AkShare  | `download_akshare_daily.py` | 日线（前复权） | `--stock-code` `--start-date` `--end-date` `--output-dir` |
| 分钟     | QMT      | `download_qmt_minute.py` | - | `--stock-code` `--target-date` `--period`(1m/5m/15m/30m/60m) `--output-dir` |
| 分钟     | Tushare  | `download_tushare_minute.py` | - | `--stock-code` `--target-date` `--freq`(1min/5min/…) `--output-dir` |
| 分钟     | AkShare  | `download_akshare_minute.py` | 仅最近 5 个交易日 | `--stock-code` `--target-date` `--period`(1/5/15/30/60) `--output-dir` |
| 财务单股 | QMT      | `download_qmt_fundamental.py` | - | `--stock-code` `--start-date` `--end-date` `--output-dir` |
| 财务单股 | Tushare  | `download_tushare_fundamental_single.py` | - | `--stock-code` `--output-dir` |
| 财务单股 | AkShare  | `download_akshare_fundamental.py` | - | `--stock-code` `--output-dir` |
| 财务批量 | Tushare  | `download_tushare_fundamental.py` | 全市场批量 | 见脚本说明 |

## 使用方式（从 prompt 传入参数）

根据用户说的“下载 XX 股票从某日到某日的日线/分钟/财务”等，提取：

- **股票代码**：如 `600519.SH`、`600519`（AkShare 日线/分钟可用纯数字）
- **时间**：日线/财务用 `--start-date`、`--end-date`（YYYYMMDD）；分钟用 `--target-date`（单日）
- **输出目录**：用户指定则用 `--output-dir`，否则默认当前目录下 `data/`

示例（命令行，参数来自用户 prompt）：

```bash
# 日线：贵州茅台 2024-01-01 到 2025-12-31，用 AkShare
python scripts/download_akshare_daily.py --stock-code 600519.SH --start-date 20240101 --end-date 20251231

# 分钟：同一只股票 2026-02-10 的 1 分钟，用 QMT
python scripts/download_qmt_minute.py --stock-code 600519.SH --target-date 20260210 --period 1m

# 财务：单只股票，用 Tushare
python scripts/download_tushare_fundamental_single.py --stock-code 600519.SH
```

Python 调用示例（参数同样应从 prompt 解析后传入）：

```python
from scripts.download_akshare_daily import download_stock_data

result = download_stock_data(
    stock_code='600519.SH',   # 由用户指定
    start_date='20240101',     # 由用户指定
    end_date='20251231',       # 由用户指定
    output_dir='./data',       # 可选，由用户指定或默认
)
```

## 数据源说明

### QMT (xtquant)
- 需安装 QMT 并配置 xtquant，分钟/财务需先启动 miniQMT 客户端
- 支持：日线、分钟（1m/5m/15m/30m/60m）、单股财务（报告期区间）

### Tushare
- 需环境变量 `TUSHARE_TOKEN`
- **日线分两种，不合并**：**历史数据**用 `download_tushare_daily.py`（pro.daily）；**复权日线**用 `download_tushare_daily_adj.py`（ts.pro_bar，前复权/后复权）。
- 分钟需单独开通权限
- 单股财务：`download_tushare_fundamental_single.py`（约 2000 积分）
- 全市场财务批量：`download_tushare_fundamental.py`

### AkShare
- 无需 Token，`pip install akshare`
- 日线/分钟/单股财务均支持；分钟仅支持最近 5 个交易日

## 输出文件约定

- 日线历史（Tushare）：`*_daily.csv`；日线复权（Tushare）：`*_daily_adj_tushare.csv`
- 日线其他：`{output_dir}/{股票代码标准化}_daily_{数据源}.csv`，如 `600519_SH_daily_akshare.csv`
- 分钟：`{output_dir}/{股票代码}_1min_{数据源}.csv`
- 财务单股：`{output_dir}/{股票代码}_fina_{数据源}.csv`

## 注意事项

1. 所有“某只股票、某段时间”均由调用方从用户 prompt 中解析后传入，脚本内不写死股票代码与时间。
2. QMT 需本地安装并启动；Tushare 需配置 `TUSHARE_TOKEN` 及对应积分权限。
3. Tushare 有频率限制；批量财务脚本支持断点续传。
