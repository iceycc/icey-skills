# -*- coding: utf-8 -*-
"""
CASE：制定你的基本面选股策略

============================================================
筛选条件（所有参数都可以在下方 CONFIG 区修改）：
============================================================
  1. 排除 ST 股和金融行业（银行/保险/证券的高杠杆是行业特性）
  2. 连续 2 年 ROE > 15%（2024、2023 年年报，已完整披露）
  3. 资产负债率 < 50%（排除高杠杆风险）
  4. 第 3 个质量条件：有经营性现金流/净利润数据时用该指标>0.8；
     当前 Tushare 数据无此项，故用「净利润同比增长>0%」（fina 表已有 netprofit_yoy）
============================================================

数据文件：data/stock_basic.csv, data/daily_basic_latest.csv, data/fina_indicator_pool.csv
（ROE 使用 2024、2023 年年报两期，避免当年报披露不全导致通过数为 0）
"""
import os
import pandas as pd


# ============================================================
# 可调参数（学员可以修改这些阈值，尝试不同的选股策略！）
# ============================================================

# ROE（净资产收益率）筛选
ROE_MIN = 15                # 每年 ROE 最低要求（%）
ROE_CONSECUTIVE_YEARS = 2   # 要求连续达标的年数（用 2024、2023 两年年报，当年报未全时更稳）

# 资产负债率筛选
DEBT_TO_ASSETS_MAX = 50     # 资产负债率上限（%）

# 经营性现金流/净利润（有数据时用）
OCF_TO_PROFIT_MIN = 0.8     # 最低要求（比率），代码会自动适配单位
# 当前 fina 无 ocf_to_profit 时，第 3 个条件用「净利润同比增长」（fina 表已有 netprofit_yoy）
NETPROFIT_YOY_MIN = 0       # 净利润同比增长 > 此值（%），过滤利润下滑或负增长
USE_NETPROFIT_YOY_WHEN_NO_OCF = True   # 无 ocf 时 True=按净利润同比筛，False=不筛第3条件

# 行业过滤
EXCLUDE_FINANCE = True      # 是否排除金融行业
EXCLUDE_ST = True           # 是否排除 ST/*ST 股

# 金融行业列表（高杠杆是行业常态，不能用通用标准衡量）
FINANCE_INDUSTRIES = ['银行', '保险', '证券', '多元金融', '信托', '租赁']

# ============================================================

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def load_data():
    """
    从本地 CSV 加载数据（由 10-数据下载-tushare财务数据.py 或 10-download_fundamental_data.py 下载）
    """
    files = {
        'stock_basic.csv': '股票列表',
        'daily_basic_latest.csv': '估值数据（市值排名用）',
        'fina_indicator_pool.csv': '财务指标',
    }

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


def determine_report_years():
    """自动确定查询的年报年份（用于理想情况）"""
    now = pd.Timestamp.now()
    if now.month >= 5:
        latest_year = now.year - 1
    else:
        latest_year = now.year - 2
    years = list(range(latest_year - ROE_CONSECUTIVE_YEARS + 1, latest_year + 1))
    return years


def get_target_periods_from_fina(fina):
    """
    根据 fina 中实际存在的报告期决定用哪些期做 ROE 筛选。
    优先用 2024、2023 两年年报（已完整披露），避免当年报（如 2025）披露不全导致通过数为 0。
    返回 (target_periods, period_desc)，period_desc 用于打印说明。
    """
    if fina is None or len(fina) == 0 or 'end_date' not in fina.columns:
        years = determine_report_years()
        return [f'{y}1231' for y in years], f"连续{ROE_CONSECUTIVE_YEARS}年（{years[0]}-{years[-1]}年）"

    raw = fina['end_date'].astype(str).str.replace('-', '').str.strip().str[:8]
    raw = raw[raw.str.match(r'^\d{8}$', na=False)]
    available = sorted(raw.unique())
    annual = [p for p in available if p.endswith('1231')]

    # 优先用 2024、2023 两年年报（已完整披露），不依赖当年报
    use_24_23 = [p for p in annual if p in ('20231231', '20241231')]
    if len(use_24_23) >= 2:
        return sorted(use_24_23), "2023、2024年年报（2期，已完整披露）"

    if len(annual) >= ROE_CONSECUTIVE_YEARS:
        use = annual[-ROE_CONSECUTIVE_YEARS:]
        return use, f"连续{ROE_CONSECUTIVE_YEARS}年（{use[0][:4]}-{use[-1][:4]}年年报）"

    if len(available) == 0:
        years = determine_report_years()
        return [f'{y}1231' for y in years], f"连续{ROE_CONSECUTIVE_YEARS}年（数据无报告期，按默认年）"

    n_use = min(ROE_CONSECUTIVE_YEARS, len(available))
    use = available[-n_use:]
    if n_use == 1:
        return use, f"最新报告期 {use[0]}（数据仅含单期）"
    return use, f"最近{n_use}期（{use[0]}～{use[-1]}）"


def detect_ocf_unit(data_series):
    """
    自动检测 ocf_to_profit 的数据单位

    通过中位数判断：
      |中位数| > 5  -> 百分比形式（85 = 85%）
      |中位数| <= 5 -> 比率形式（0.85 = 85%）
    """
    valid = data_series.dropna()
    if len(valid) == 0:
        return OCF_TO_PROFIT_MIN, "无数据"

    median_val = valid.median()
    if abs(median_val) > 5:
        threshold = OCF_TO_PROFIT_MIN * 100
        unit_desc = f"百分比形式（中位数={median_val:.1f}），阈值={threshold:.0f}%"
    else:
        threshold = OCF_TO_PROFIT_MIN
        unit_desc = f"比率形式（中位数={median_val:.2f}），阈值={threshold}"

    return threshold, unit_desc


def run_screener():
    """
    多因子基本面选股
    纯本地数据分析，无 API 调用，秒出结果
    """
    # ---- 加载数据 ----
    stocks, daily, fina = load_data()
    if stocks is None:
        return

    target_periods, period_desc = get_target_periods_from_fina(fina)
    years = [p[:4] for p in target_periods]

    print("=" * 70)
    print("CASE：制定你的基本面选股策略")
    print("=" * 70)
    print("筛选条件：")
    print(f"  [1] ROE > {ROE_MIN}%：{period_desc}")
    print(f"  [2] 资产负债率 < {DEBT_TO_ASSETS_MAX}%")
    print(f"  [3] 净利润同比增长 > {NETPROFIT_YOY_MIN}%（当前无经营性现金流/净利润数据，用 fina 表 netprofit_yoy）")
    if EXCLUDE_FINANCE:
        print(f"  [X] 排除金融行业：{FINANCE_INDUSTRIES}")
    if EXCLUDE_ST:
        print(f"  [X] 排除 ST/*ST 股")
    print("=" * 70)

    # 漏斗计数
    funnel = []

    # ================================================================
    # Step 1：全市场股票
    # ================================================================
    total_all = len(stocks)
    funnel.append(('全市场上市股票', total_all))
    print(f"\n[Step 1] 全市场：{total_all} 只")

    # 只保留在数据池中有财务数据的股票（fina 表中有记录的才参与后续筛选）
    fina_codes = set(fina['ts_code'].unique())
    pool = stocks[stocks['ts_code'].isin(fina_codes)].copy()
    funnel.append(('数据池中有财务数据', len(pool)))
    print(f"[Step 2] 数据池中有财务数据：{len(pool)} 只（fina 表仅有此数量；若为 Tushare 单期下载属正常）")

    # ================================================================
    # Step 3：排除 ST 股
    # ================================================================
    if EXCLUDE_ST:
        before = len(pool)
        pool = pool[~pool['name'].str.contains('ST', case=False, na=False)]
        removed = before - len(pool)
        funnel.append(('排除ST股', len(pool)))
        print(f"[Step 3] 排除 ST 股：去掉 {removed} 只 -> 剩余 {len(pool)} 只")

    # ================================================================
    # Step 4：排除金融行业
    # ================================================================
    if EXCLUDE_FINANCE:
        before = len(pool)
        pool = pool[~pool['industry'].isin(FINANCE_INDUSTRIES)]
        removed = before - len(pool)
        funnel.append(('排除金融行业', len(pool)))
        print(f"[Step 4] 排除金融行业：去掉 {removed} 只 -> 剩余 {len(pool)} 只")

    pool_codes = set(pool['ts_code'].tolist())

    # 筛选本池内的财务数据，并统一 end_date 为 8 位便于比较
    fina_pool = fina[fina['ts_code'].isin(pool_codes)].copy()
    fina_pool['_end8'] = fina_pool['end_date'].astype(str).str.replace('-', '').str[:8]

    # ---- 数据校验：用贵州茅台验证单位 ----
    print("\n  [数据校验] 贵州茅台各报告期数据：")
    maotai_code = '600519.SH'
    for period in target_periods:
        p8 = str(period)[:8]
        mt = fina_pool[(fina_pool['ts_code'] == maotai_code) & (fina_pool['_end8'] == p8)]
        if len(mt) > 0:
            row = mt.iloc[0]
            parts = []
            for col, label in [('roe', 'ROE'), ('debt_to_assets', '负债率'),
                               ('ocf_to_profit', '现金流/利润')]:
                val = row.get(col)
                if pd.notna(val):
                    parts.append(f"{label}={val:.2f}")
                else:
                    parts.append(f"{label}=N/A")
            print(f"    {period}: {', '.join(parts)}")
        else:
            print(f"    {period}: 无数据")

    # ================================================================
    # Step 5：ROE 筛选（多期则要求每期都 > ROE_MIN，单期则要求该期 > ROE_MIN）
    # ================================================================
    step5_desc = f"ROE>{ROE_MIN}%（共{len(target_periods)}期）" if len(target_periods) > 1 else f"ROE>{ROE_MIN}%（最新报告期）"
    print(f"\n[Step 5] {step5_desc}...")

    # 将多期 ROE 横向合并（每期一列，已用 _end8）
    roe_merged = None
    for period in target_periods:
        p8 = str(period)[:8]
        year_str = p8[:4]
        year_data = fina_pool[fina_pool['_end8'] == p8][['ts_code', 'roe']].copy()
        year_data = year_data.rename(columns={'roe': f'roe_{year_str}'})
        year_data = year_data.drop_duplicates(subset='ts_code', keep='last')

        if roe_merged is None:
            roe_merged = year_data
        else:
            roe_merged = roe_merged.merge(year_data, on='ts_code', how='inner')

    if roe_merged is None or len(roe_merged) == 0:
        print("  没有股票拥有完整的 ROE 数据（请检查 fina 表是否含对应报告期）")
        _print_funnel(funnel)
        return

    print(f"  {len(target_periods)} 期都有 ROE 数据：{len(roe_merged)} 只")

    # 每一期都要 > ROE_MIN
    roe_condition = pd.Series([True] * len(roe_merged), index=roe_merged.index)
    for period in target_periods:
        col = f'roe_{str(period)[:4]}'
        if col in roe_merged.columns:
            roe_condition = roe_condition & (roe_merged[col] > ROE_MIN)

    roe_pass = roe_merged[roe_condition].copy()
    funnel.append((step5_desc, len(roe_pass)))
    print(f"  通过 ROE 筛选：{len(roe_pass)} 只")

    if len(roe_pass) == 0:
        print("  没有股票通过，建议降低 ROE_MIN 或减少 ROE_CONSECUTIVE_YEARS")
        _print_funnel(funnel)
        return

    passed_codes = set(roe_pass['ts_code'].tolist())

    # ================================================================
    # Step 6：资产负债率 < 50%
    # ================================================================
    print(f"\n[Step 6] 资产负债率 < {DEBT_TO_ASSETS_MAX}%...")

    latest_period = str(target_periods[-1])[:8]
    latest_data = fina_pool[fina_pool['_end8'] == latest_period].copy()
    latest_data = latest_data[latest_data['ts_code'].isin(passed_codes)]
    latest_data = latest_data.drop_duplicates(subset='ts_code', keep='last')

    debt_valid = latest_data.dropna(subset=['debt_to_assets'])
    debt_pass = debt_valid[debt_valid['debt_to_assets'] < DEBT_TO_ASSETS_MAX]
    funnel.append((f'负债率<{DEBT_TO_ASSETS_MAX}%', len(debt_pass)))
    print(f"  有数据 {len(debt_valid)} 只，通过 {len(debt_pass)} 只")

    if len(debt_pass) == 0:
        print("  没有股票通过负债率筛选")
        _print_funnel(funnel)
        return

    passed_codes = set(debt_pass['ts_code'].tolist())

    # ================================================================
    # Step 7：第 3 个质量条件（有 ocf 用现金流/利润，无则用净利润同比增长）
    # ================================================================
    ocf_data = latest_data[latest_data['ts_code'].isin(passed_codes)].copy()
    ocf_valid = ocf_data.dropna(subset=['ocf_to_profit'])

    if len(ocf_valid) == 0:
        print(f"\n[Step 7] 净利润同比增长 > {NETPROFIT_YOY_MIN}%（当前无经营性现金流/净利润数据）...")
        if USE_NETPROFIT_YOY_WHEN_NO_OCF and 'netprofit_yoy' in ocf_data.columns:
            ny_valid = ocf_data.dropna(subset=['netprofit_yoy'])
            ocf_pass = ny_valid[ny_valid['netprofit_yoy'] > NETPROFIT_YOY_MIN] if len(ny_valid) > 0 else ocf_data
            n_drop = len(ocf_data) - len(ocf_pass)
            funnel.append((f'净利润同比>{NETPROFIT_YOY_MIN}%', len(ocf_pass)))
            print(f"  有数据 {len(ny_valid)} 只，通过 {len(ocf_pass)} 只（去掉 {n_drop} 只）")
        else:
            ocf_pass = ocf_data
            funnel.append(('第3条件未筛', len(ocf_pass)))
            print(f"  未启用第 3 条件，通过 {len(ocf_pass)} 只")
    else:
        print(f"\n[Step 7] 经营性现金流/净利润 > {OCF_TO_PROFIT_MIN}...")
        actual_threshold, unit_desc = detect_ocf_unit(ocf_valid['ocf_to_profit'])
        print(f"  单位检测：{unit_desc}")
        ocf_pass = ocf_valid[ocf_valid['ocf_to_profit'] > actual_threshold]
        funnel.append(('现金流/利润达标', len(ocf_pass)))
        print(f"  有数据 {len(ocf_valid)} 只，通过 {len(ocf_pass)} 只")

    final_codes = set(ocf_pass['ts_code'].tolist())

    # ================================================================
    # 组装最终结果
    # ================================================================
    final = pool[pool['ts_code'].isin(final_codes)].copy()

    # 附加最新财务指标
    attach_cols = ['ts_code', 'roe', 'debt_to_assets', 'ocf_to_profit', 'netprofit_yoy']
    attach_cols = [c for c in attach_cols if c in latest_data.columns]
    final = final.merge(
        latest_data[attach_cols].drop_duplicates(subset='ts_code', keep='last'),
        on='ts_code', how='left'
    )

    # 附加各年 ROE
    roe_year_cols = [f'roe_{p[:4]}' for p in target_periods]
    roe_cols_to_add = ['ts_code'] + roe_year_cols
    final = final.merge(roe_pass[roe_cols_to_add], on='ts_code', how='left')

    # 按最新 ROE 从高到低排序
    final = final.sort_values('roe', ascending=False).reset_index(drop=True)

    # ================================================================
    # 输出结果
    # ================================================================
    print("\n")
    _print_funnel(funnel)

    if len(final) == 0:
        print("\n没有符合所有条件的股票")
        print("建议：降低 ROE_MIN 或放宽 DEBT_TO_ASSETS_MAX")
        return

    # 表格：第 3 个指标有 ocf 则展示现金流/利润，无则展示净利润同比
    display_cols = ['ts_code', 'name', 'industry'] + roe_year_cols + ['debt_to_assets']
    if 'ocf_to_profit' in final.columns and final['ocf_to_profit'].notna().any():
        display_cols.append('ocf_to_profit')
    elif 'netprofit_yoy' in final.columns:
        display_cols.append('netprofit_yoy')
    display_cols = [c for c in display_cols if c in final.columns]
    display = final[display_cols].copy()

    col_names = ['代码', '名称', '行业']
    for p in target_periods:
        col_names.append(f'ROE{p[:4]}')
    col_names.append('负债率(%)')
    if 'ocf_to_profit' in display_cols:
        col_names.append('现金流/利润')
    elif 'netprofit_yoy' in display_cols:
        col_names.append('净利润同比(%)')
    display.columns = col_names[:len(display.columns)]

    for col in display.columns:
        if display[col].dtype in ['float64', 'float32']:
            display[col] = display[col].round(2)

    pd.set_option('display.unicode.ambiguous_as_wide', True)
    pd.set_option('display.unicode.east_asian_width', True)
    pd.set_option('display.max_columns', 20)
    pd.set_option('display.width', 200)

    print(f"\n最终入选（共 {len(final)} 只，按最新 ROE 从高到低）：")
    print("-" * 70)

    show_n = min(50, len(display))
    print(display.head(show_n).to_string(index=False))
    if len(display) > show_n:
        print(f"\n... 还有 {len(display) - show_n} 只，完整结果见CSV文件")

    # ---- 行业分布 ----
    print("\n" + "-" * 70)
    print("行业分布（什么行业容易出\"好公司\"？）：")
    print("-" * 70)
    industry_stats = final['industry'].value_counts().head(15)
    if len(industry_stats) > 0:
        max_count = industry_stats.iloc[0]
        for ind_name, count in industry_stats.items():
            bar_len = int(count / max_count * 30)
            print(f"  {ind_name:<10s} {count:>3d} 只  {'#' * bar_len}")

    # ---- ROE 趋势 ----
    print("\n" + "-" * 70)
    print(f"入选股票 ROE 趋势（{years[0]}-{years[-1]}年平均值）：")
    for p in target_periods:
        col = f'roe_{p[:4]}'
        if col in final.columns:
            avg_roe = final[col].mean()
            print(f"  {p[:4]} 年平均 ROE：{avg_roe:.2f}%")

    # ---- 教学要点 ----
    total_start = funnel[0][1]
    print("\n" + "=" * 70)
    print("教学要点")
    print("=" * 70)
    print(f"  1. 从 {total_start} 只 -> {len(final)} 只："
          f"这就是量化选股的\"漏斗\"思维")
    print(f"  2. 连续{ROE_CONSECUTIVE_YEARS}年 ROE>{ROE_MIN}%"
          f" 是巴菲特核心标准（他要求15%以上）")
    print(f"  3. 排除金融股：银行/保险的高杠杆是行业特性，"
          f"不能用<{DEBT_TO_ASSETS_MAX}%标准衡量")
    print(f"  4. 现金流/利润>{OCF_TO_PROFIT_MIN * 100:.0f}% "
          f"排除\"纸面利润\"：")
    print(f"     - 应收账款堆积（卖了货但没收到钱）")
    print(f"     - 关联交易虚增收入")
    print(f"     - 经典案例：某环保公司利润好看但现金流为负")
    print(f"  5. 筛出来 =/= 可以直接买！还需要看估值（PE/PB是否合理）")
    print(f"")
    print(f"  进阶思考：")
    print(f"  - 把 ROE_MIN 改成 20%，还剩多少只？")
    print(f"  - 加条件：netprofit_yoy > 10%（净利润同比增长>10%）")
    print(f"  - 看看结果中有没有你熟悉的公司？")
    print("=" * 70)

    # ---- 保存 ----
    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, '11-综合基本面选股_result.csv')
    save_cols = ['ts_code', 'name', 'industry'] + roe_year_cols + ['debt_to_assets', 'netprofit_yoy']
    if 'ocf_to_profit' in final.columns and final['ocf_to_profit'].notna().any():
        save_cols.insert(save_cols.index('netprofit_yoy'), 'ocf_to_profit')
    save_cols = [c for c in save_cols if c in final.columns]
    final[save_cols].to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"\n完整结果已保存：{out_path}")


def _print_funnel(funnel):
    """打印筛选漏斗"""
    print("=" * 70)
    print("筛选漏斗：从全市场到优质公司")
    print("=" * 70)
    for i, (desc, cnt) in enumerate(funnel):
        if i == 0:
            print(f"  {desc:<30s}  {cnt:>5d} 只")
        else:
            prev_cnt = funnel[i - 1][1]
            removed = prev_cnt - cnt
            print(f"  -> {desc:<28s}  {cnt:>5d} 只  (去掉 {removed})")
    print("=" * 70)


if __name__ == '__main__':
    run_screener()
