# Skills

本仓库包含多类 Agent Skills，涵盖通用工具、股票分析、内容监控等。

## Skills 列表

### 通用 / 工具类

| Skill | 说明 |
|-------|------|
| **weather** | 天气查询（wttr.in / Open-Meteo），无需 API Key。支持当前天气、预报、PNG 图。 |
| **summarize** | 对 URL、本地文件、YouTube 链接做摘要或提取转录。触发：摘要链接/文章、转录视频。需安装 `summarize`（如 `brew install steipete/tap/summarize`）。 |
| **skill-creator** | 创建或更新 Agent Skills。用于设计、结构化、打包含脚本/参考文档/资源的 skill。 |
| **memory** | 双层记忆：`MEMORY.md` 长期事实，`HISTORY.md` 事件日志。用 grep 检索历史。 |
| **cron** | 定时提醒与周期任务（提醒 / 任务执行 / 单次定时），支持 cron 表达式与时区。 |
| **clawhub** | 从 ClawHub 公共 skill 仓库搜索、安装、更新 skills。触发：找 skill、安装 skill、更新 skills。 |
| **github** | 使用 `gh` CLI 与 GitHub 交互：issue、PR、CI runs、`gh api` 高级查询。 |
| **tmux** | 通过发送按键与抓取 pane 输出远程控制 tmux 会话，适用于交互式 CLI、多 agent 并行。仅 macOS/Linux，需安装 tmux。 |
| **obsidian** | 操作 Obsidian 库（纯 Markdown），配合 obsidian-cli：搜索、创建/移动/删除笔记、解析当前库。需安装 obsidian-cli。 |

### 股票 / 金融分析

| Skill | 说明 |
|-------|------|
| **stock-data-download** | 从 QMT、Tushare、AkShare 下载日线（含复权）、分钟、财务数据。股票代码、时间、输出目录由 prompt 或参数传入。 |
| **stock-visualization** | K 线图、成交量图、多指标仪表盘（MA、RSI、ATR、成交量等）。 |
| **technical-indicators** | MA/MACD/RSI/ATR 计算与交易信号（金叉/死叉、超买超卖、止损位）。 |
| **fundamental-analysis** | 财务指标获取（PE、PB、ROE 等）、格雷厄姆 PB 选股、多因子基本面选股。 |

### 内容 / 媒体

| Skill | 说明 |
|-------|------|
| **bilibili-monitor** | 生成 B 站热门视频日报并发送邮件。触发：B站热门、bilibili日报、视频日报、热门视频。支持 AI 总结与点评（需 OpenRouter）。 |

---

## 股票分析使用流程

### 1. 数据下载
```bash
# stock-data-download
python skills/stock-data-download/scripts/download_tushare_daily.py --stock-code 600519.SH --start-date 20240101 --end-date 20251231
python skills/stock-data-download/scripts/download_tushare_fundamental.py  # 批量财务
```

### 2. 数据可视化
```bash
# stock-visualization
python skills/stock-visualization/scripts/plot_kline_volume.py
python skills/stock-visualization/scripts/plot_indicator_dashboard.py
```

### 3. 技术指标分析
```bash
# technical-indicators
python skills/technical-indicators/scripts/calc_ma_signals.py
python skills/technical-indicators/scripts/calc_macd_signals.py
python skills/technical-indicators/scripts/calc_rsi.py
python skills/technical-indicators/scripts/calc_atr.py
```

### 4. 基本面分析
```bash
# fundamental-analysis
python skills/fundamental-analysis/scripts/get_financial_indicators.py
python skills/fundamental-analysis/scripts/graham_pb_screener.py
python skills/fundamental-analysis/scripts/multi_factor_screener.py
```

---

## 依赖与环境

### 通用依赖
- 部分 skill 需要：`curl`、`python3`、`tmux`、`gh`、`obsidian-cli`、`summarize`、`npx`（Node.js）等，见各 skill 的 SKILL.md。

### 股票相关
- pandas、numpy、matplotlib
- tushare（需 `TUSHARE_TOKEN`）、xtquant（QMT）、akshare

### 环境变量示例
- `TUSHARE_TOKEN` — Tushare API Token（股票数据）
- 各 AI/摘要类：`OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`GEMINI_API_KEY` 等（见 summarize / bilibili-monitor 说明）

---

## 目录结构

每个 skill 建议结构：

```
skill-name/
├── SKILL.md          # 说明与触发条件（必选）
├── scripts/          # 可执行脚本（可选）
├── references/       # 参考文档（可选）
└── assets/           # 资源文件（可选）
```

---

## 注意事项

1. 股票类 skills 建议先使用 **stock-data-download** 准备数据。
2. Tushare 需配置 `TUSHARE_TOKEN` 及相应积分权限。
3. 数据文件默认放在 `data/`，图表输出默认在 `outputs/`。
4. 部分 skill 仅在特定系统可用（如 tmux 为 darwin/linux）。
5. 安装新 skill 后建议新开会话以加载。
