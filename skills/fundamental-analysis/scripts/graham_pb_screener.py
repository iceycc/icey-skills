# -*- coding: utf-8 -*-
"""
CASE：格雷厄姆的低PB策略（捡烟蒂选股器）

核心思想：
  格雷厄姆认为：当一家公司的市场价格低于其账面净资产（PB<1），
  就像捡别人扔掉的烟蒂，虽然只剩一口，但那一口是免费的。

筛选条件：
  - PB < 1（破净：市场给价低于公司净资产，相当于"清算价"买入）
  - ROE > 5%（仍在赚钱，排除亏损的垃圾股）

数据文件：data/stock_basic.csv, data/daily_basic_latest.csv, data/fina_indicator_pool.csv
"""
import os
import sys
import pandas as pd


# ============================================================
# 可调参数（学员可以修改试试不同组合！）
# ============================================================
PB_MAX = 1.0           # PB 上限：低于此值为"破净"
ROE_MIN = 5.0          # ROE 下限（%）：高于此值说明公司还在赚钱
# ============================================================

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def load_data():
    """
    从本地 CSV 加载数据（由 10-数据下载-tushare财务数据.py 或 10-download_fundamental_data.py 下载）
    返回：stocks, daily, fina 三个 DataFrame
    """
    files = {
        'stock_basic.csv': '股票列表',
        'daily_basic_latest.csv': '估值数据',
        'fina_indicator_pool.csv': '财务指标',
    }

    # 检查文件是否存在
    missing = []
    for fname, desc in files.items():
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath):
            missing.append(f"  {fname}（{desc}）")

    if missing:
        print("错误：缺少数据文件，请先运行数据下载脚本")
        print("缺少的文件：")
        for m in missing:
            print(m)
        print("\n请执行：python 10-数据下载-tushare财务数据.py  或  python 10-download_fundamental_data.py")
        return None, None, None

    # 加载数据
    stocks = pd.read_csv(
        os.path.join(DATA_DIR, 'stock_basic.csv'),
        dtype={'ts_code': str},
        encoding='utf-8-sig'
    )
    daily = pd.read_csv(
        os.path.join(DATA_DIR, 'daily_basic_latest.csv'),
        dtype={'ts_code': str},
        encoding='utf-8-sig'
    )
    fina = pd.read_csv(
        os.path.join(DATA_DIR, 'fina_indicator_pool.csv'),
        dtype={'ts_code': str, 'end_date': str},
        encoding='utf-8-sig'
    )

    return stocks, daily, fina


def get_report_period_from_fina(fina):
    """从财务数据中取报告期，优先使用 2024 年年报 20241231（披露更全），否则取数据中最新报告期。"""
    if fina is None or len(fina) == 0 or 'end_date' not in fina.columns:
        now = pd.Timestamp.now()
        year = now.year - 1 if now.month >= 5 else now.year - 2
        return f'{year}1231', str(year)
    end8 = fina['end_date'].astype(str).str.replace('-', '').str.strip().str[:8]
    available = end8[end8.str.match(r'^\d{8}$', na=False)].unique()
    # 优先 2024 年年报（披露更全、数据更稳）
    if '20241231' in available:
        return '20241231', '2024'
    period = end8[end8.str.match(r'^\d{8}$', na=False)].max()
    if pd.isna(period) or period == '':
        period = f'{pd.Timestamp.now().year - 1}1231'
    period = str(period)[:8]
    roe_year = period[:4]
    return period, roe_year


def run_screener():
    """
    格雷厄姆"捡烟蒂"选股器
    纯本地数据分析，无 API 调用，秒出结果
    """
    # ---- 加载数据 ----
    stocks, daily, fina = load_data()
    if stocks is None:
        return

    period, roe_year = get_report_period_from_fina(fina)

    # 获取估值数据日期
    trade_date = ''
    if 'trade_date' in daily.columns and len(daily) > 0:
        td = str(daily['trade_date'].iloc[0])
        trade_date = f"{td[:4]}-{td[4:6]}-{td[6:8]}" if len(td) >= 8 else td

    print("=" * 70)
    print(f"筛选条件：PB < {PB_MAX}（破净）且 ROE > {ROE_MIN}%（仍盈利）")
    print(f"估值日期：{trade_date}    ROE来源：{roe_year}年报告期 {period}")
    print("=" * 70)

    # ---- 排除 ST 股 ----
    st_mask = stocks['name'].str.contains('ST', case=False, na=False)
    stocks_clean = stocks[~st_mask].copy()
    print(f"\n全市场 {len(stocks)} 只，排除 {st_mask.sum()} 只ST股，剩余 {len(stocks_clean)} 只")

    # ---- 合并 PB 数据 ----
    merged = stocks_clean.merge(
        daily[['ts_code', 'close', 'pb', 'pe', 'total_mv']],
        on='ts_code', how='inner'
    )
    merged = merged.dropna(subset=['pb'])
    print(f"有 PB 数据的：{len(merged)} 只")

    # ---- 合并 ROE 数据（取数据中最新报告期） ----
    fina_end8 = fina['end_date'].astype(str).str.replace('-', '').str[:8]
    fina_latest = fina[fina_end8 == period].copy()
    fina_latest = fina_latest.drop_duplicates(subset='ts_code', keep='last')
    merged = merged.merge(fina_latest[['ts_code', 'roe']], on='ts_code', how='inner')
    merged = merged.dropna(subset=['roe'])
    print(f"有 PB + ROE 数据的：{len(merged)} 只")

    # ============================================================
    # 核心筛选 -- 一行代码！这就是 pandas 的威力
    # ============================================================
    final = merged[
        (merged['pb'] > 0) &           # PB 为正（负值=净资产为负，更危险）
        (merged['pb'] < PB_MAX) &      # PB < 1：破净
        (merged['roe'] > ROE_MIN)      # ROE > 5%：还在赚钱
    ].copy()
    final = final.sort_values('pb').reset_index(drop=True)
    # ============================================================

    # ---- 输出结果 ----
    print("\n" + "=" * 70)
    print("筛选结果")
    print("=" * 70)
    pb_candidates = merged[(merged['pb'] > 0) & (merged['pb'] < PB_MAX)]
    print(f"  破净候选（PB<{PB_MAX}）：{len(pb_candidates)} 只")
    print(f"  加 ROE>{ROE_MIN}% 后：{len(final)} 只")
    print("-" * 70)

    if len(final) == 0:
        print("没有同时满足条件的股票，建议放宽 PB_MAX 或降低 ROE_MIN")
        return

    # 表格展示
    display = final[['ts_code', 'name', 'industry', 'close', 'pb', 'roe', 'total_mv']].copy()
    display['total_mv'] = (display['total_mv'] / 10000).round(1)
    display['pb'] = display['pb'].round(3)
    display['roe'] = display['roe'].round(2)
    display.columns = ['代码', '名称', '行业', '收盘价', 'PB', 'ROE(%)', '市值(亿)']

    pd.set_option('display.unicode.ambiguous_as_wide', True)
    pd.set_option('display.unicode.east_asian_width', True)
    pd.set_option('display.width', 200)

    show_n = min(30, len(display))
    print(f"\n前 {show_n} 只（按 PB 从低到高）：")
    print("-" * 70)
    print(display.head(show_n).to_string(index=False))
    if len(display) > show_n:
        print(f"\n... 还有 {len(display) - show_n} 只，完整结果见CSV文件")

    # ---- 行业分布 ----
    print("\n" + "-" * 70)
    print("行业分布（破净股集中在哪些行业？）：")
    print("-" * 70)
    industry_stats = final['industry'].value_counts().head(15)
    max_count = industry_stats.iloc[0] if len(industry_stats) > 0 else 1
    for ind_name, count in industry_stats.items():
        bar_len = int(count / max_count * 30)
        print(f"  {ind_name:<10s} {count:>3d} 只  {'#' * bar_len}")

    # ---- PB 分布 ----
    print("\n" + "-" * 70)
    print("PB 分布：")
    print(f"  最低：{final['pb'].min():.3f}（{final.iloc[0]['name']}）")
    print(f"  最高：{final['pb'].max():.3f}")
    print(f"  平均：{final['pb'].mean():.3f}")
    print(f"  中位：{final['pb'].median():.3f}")

    # ---- 保存 ----
    out_path = os.path.join(DATA_DIR, '10-格雷厄姆PB选股_result.csv')
    save_cols = ['ts_code', 'name', 'industry', 'close', 'pb', 'roe', 'pe', 'total_mv']
    save_cols = [c for c in save_cols if c in final.columns]
    final[save_cols].to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"\n完整结果已保存：{out_path}")


if __name__ == '__main__':
    run_screener()
