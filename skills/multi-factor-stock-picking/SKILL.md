---
name: multi-factor-stock-picking
description: 多因子选股工作流：通过 QMT 下载板块内股票财务数据池，再按绝对阈值或行业内打分筛选。用于批量获取财务指标池、按 ROE/毛利率/负债率/现金流等条件筛选股票。当需要多因子选股、财务池下载、绝对阈值或行业相对打分筛选时使用。
---

# 多因子选股

提供「下载财务池 → 筛选」两步工作流，板块、日期、阈值等通过命令行或参数传入。

## 流程概览

1. **下载数据**：`scripts/download_fina_pool_qmt.py` — 从 QMT 拉取指定板块内所有股票的财务数据，输出「财务池」CSV（含 ROE、净利润同比、毛利率、资产负债率、经营现金流/营收等 + 股票名称、申万一级行业）。
2. **筛选1（绝对阈值）**：`scripts/screen_absolute.py` — 5 层漏斗：ROE≥、净利润同比≥、毛利率≥、资产负债率≤、经营现金流/营收≥，输出达标股票。
3. **筛选2（行业打分）**：`scripts/screen_industry.py` — 按行业内排名将 5 项指标换算为 1~5 分，总分≥阈值筛选，可输出行业分布图。

## 脚本与参数

| 脚本 | 说明 | 主要参数 |
|------|------|----------|
| `download_fina_pool_qmt.py` | 下载财务池（QMT） | `--sector` `--start-date` `--end-date` `--output-dir` `--num-workers` |
| `screen_absolute.py` | 绝对阈值筛选 | `--input-file` `--output-file`，或 `--data-dir`；阈值 `--roe-min` `--netprofit-yoy-min` 等 |
| `screen_industry.py` | 行业打分筛选 | `--input-file` `--output-file` `--score-min` `--viz`/`--no-viz` |

默认输入/输出：`data/stock_fina_pool_QMT.csv` → 筛选1 输出 `data/stock_fina_selected_QMT.csv`，筛选2 输出 `data/stock_fina_selected_QMT_industry.csv`、`data/industry_viz/*.png`。

## 使用方式

### 1. 下载财务池（需 QMT + miniQMT）

```bash
python scripts/download_fina_pool_qmt.py --sector "沪深A股" --start-date 20150101 --end-date 20251231 --output-dir ./data
```

### 2. 绝对阈值筛选

```bash
python scripts/screen_absolute.py --data-dir ./data --roe-min 15 --netprofit-yoy-min 10 --grossprofit-margin-min 30 --debt-to-assets-max 60 --ocf-to-revenue-min 10
```

### 3. 行业打分筛选

```bash
python scripts/screen_industry.py --input-file ./data/stock_fina_pool_QMT.csv --output-file ./data/stock_fina_selected_QMT_industry.csv --score-min 18 --viz
```

## 数据依赖

- 下载脚本依赖 **QMT（xtquant）**，运行前需启动 miniQMT。
- 筛选脚本仅依赖上一步生成的 `stock_fina_pool_QMT.csv`（列含 `stock_code`, `stock_name`, `industry`, `end_date`, `roe`, `netprofit_yoy`, `grossprofit_margin`, `debt_to_assets`, `ocf_to_revenue` 等）。

## 注意事项

1. 板块名需与 QMT 板块列表一致（如「沪深A股」）。
2. 筛选结果仅供研究参考，不构成投资建议。
