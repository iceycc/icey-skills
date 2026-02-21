# -*- coding: utf-8 -*-
"""
基本面选股 -- 数据下载脚本（Tushare 版）

使用 Tushare Pro 获取股票列表、财务指标、指定日行情，无需 QMT。

下载内容：
  1. 股票列表（代码/名称/行业） -- pro.stock_basic
  2. 指定日行情（收盘价/PE/PB/市值） -- pro.daily_basic
  3. 财务指标（ROE/BPS/EPS/负债率等） -- pro.fina_indicator

保存文件（均在 data/ 目录下）：
  - stock_basic.csv          -- 股票列表
  - daily_basic_latest.csv   -- 指定日估值（close, pb, pe, total_mv）
  - fina_indicator_pool.csv  -- 财务指标（roe, bps, eps, debt_to_assets 等）

环境：pip install tushare，并设置环境变量 TUSHARE_TOKEN
"""
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pandas as pd

from tushare_pro import get_pro


# ============================================================
# 配置
# ============================================================

# 基准交易日（用于行情与估值），取该日或之前最近的数据
TRADE_DATE = "20260206"

# True=按当前日期自动取「最近报告期」（三季报/半年报/一季报，不一定是年报）；False=用下面固定值
REPORT_USE_LATEST = True
# 仅当 REPORT_USE_LATEST=False 时生效，固定报告期（如年报 20241231）
REPORT_END_YEAR = 2024
REPORT_PERIOD_FIXED = f"{REPORT_END_YEAR}1231"
# 说明：用最近报告期时，选股器会按 fina 表内最大 end_date 取数，可直接用

# True=拉取多报告期（最近3期年报），供 11 做「连续3年 ROE」等；False=只拉单期
USE_MULTIPLE_PERIODS = True
# 多报告期时使用的年报期数（最近 N 期年报，如 20241231, 20231231, 20221231）
NUM_ANNUAL_PERIODS = 3

# 每批请求条数，每批完成后立即合并保存到 CSV，断线重跑不会重复下载
BATCH_SIZE = 500
# 并行线程数
NUM_WORKERS = 3
# 请求间隔（秒），500 次/分钟 => 0.12 秒/次，全程节流不触发限频
REQUEST_INTERVAL = 0.12

# ============================================================

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def get_latest_report_period():
    """
    按当前日期推算「最近已披露报告期」（不一定是年报）。
    规则：10 月及以后用当年三季报(0930)，8-9 月用半年报(0630)，4-7 月用一季报(0331)，
    1-3 月用上一年三季报(上年0930)。
    """
    now = datetime.now()
    y, m = now.year, now.month
    if m >= 10:
        return f"{y}0930"
    if m >= 8:
        return f"{y}0630"
    if m >= 4:
        return f"{y}0331"
    return f"{y - 1}0930"


def get_report_periods_annual(n=3):
    """
    返回最近 n 期年报报告期（如 [20241231, 20231231, 20221231]），用于多期 ROE 等。
    """
    now = datetime.now()
    y = now.year
    # 若当前在 1-4 月，上年年报可能未全披露，从上年起算
    if now.month < 4:
        y -= 1
    return [f"{y - i}1231" for i in range(n)]


# ================================================================
# Step 1：股票列表（代码、名称、行业）
# ================================================================
def step1_stock_info(pro):
    """从 Tushare 获取 A 股股票列表"""
    print("[Step 1/3] 获取 A 股股票列表...")
    try:
        df = pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,name,industry,market"
        )
    except Exception as e:
        print(f"  请求失败: {e}")
        return pd.DataFrame()

    if df is None or len(df) == 0:
        print("  未返回数据")
        return pd.DataFrame()

    # 只保留 A 股（沪/深）
    df = df[df["ts_code"].str.endswith((".SH", ".SZ"), na=False)].copy()
    df["industry"] = df.get("industry", pd.Series(dtype=object)).fillna("")
    # 兼容下游：symbol, market
    df["symbol"] = df["ts_code"].str.split(".").str[0]
    df["market"] = df["ts_code"].str.split(".").str[1]
    df = df[["ts_code", "name", "industry", "symbol", "market"]]

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "stock_basic.csv")
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"  已保存 {len(df)} 只股票 -> {out_path}")
    return df


# ================================================================
# Step 2：财务指标（ROE、BPS、EPS、负债率等）
# ================================================================
_request_lock = threading.Lock()
_last_request_time = [0.0]
_print_error_lock = threading.Lock()
_api_error_printed = set()
# 本批失败原因统计：每批开始时清空，请求失败时追加 "limit" 或 "other"，用于打印是限频还是无数据
_batch_error_types = []
_batch_error_lock = threading.Lock()


def _fetch_one_fina(pro, report_period, ts_code):
    """单只股票拉取财务指标。全程按 REQUEST_INTERVAL 节流，保证不超 500 次/分钟。"""
    with _request_lock:
        now = time.time()
        wait = _last_request_time[0] + REQUEST_INTERVAL - now
        if wait > 0:
            time.sleep(wait)
        _last_request_time[0] = time.time()
    try:
        df = pro.fina_indicator(
            ts_code=ts_code,
            period=report_period,
            fields="ts_code,end_date,roe,bps,eps,debt_to_assets,netprofit_yoy"
        )
        if df is None or len(df) == 0:
            return None
        row = df.iloc[0]
        end_date = str(row.get("end_date", report_period)).replace("-", "").strip()[:8]
        return {
            "ts_code": ts_code,
            "end_date": end_date,
            "roe": float(row["roe"]) if pd.notna(row.get("roe")) else None,
            "bps": float(row["bps"]) if pd.notna(row.get("bps")) else None,
            "eps": float(row["eps"]) if pd.notna(row.get("eps")) else None,
            "debt_to_assets": float(row["debt_to_assets"]) if pd.notna(row.get("debt_to_assets")) else None,
            "ocf_to_profit": None,
            "netprofit_yoy": float(row["netprofit_yoy"]) if pd.notna(row.get("netprofit_yoy")) else None,
        }
    except Exception as e:
        err_msg = str(e) if e else ""
        is_limit = "权限" in err_msg or "限制" in err_msg or "超过" in err_msg or "limit" in err_msg.lower()
        with _batch_error_lock:
            _batch_error_types.append("limit" if is_limit else "other")
        with _print_error_lock:
            key = (err_msg[:80],)
            if key not in _api_error_printed:
                _api_error_printed.add(key)
                print(f"  [API] 接口报错: {err_msg[:200]}")
        return None


def _merge_and_save_fina(out_path, current_df, batch_records, cols):
    """将本批 batch_records 合并进 current_df，去重后保存。"""
    if not batch_records:
        return current_df
    new_df = pd.DataFrame(batch_records)
    new_df["_end8"] = new_df["end_date"].astype(str).str.replace("-", "").str[:8]
    keys_new = set(zip(new_df["ts_code"].tolist(), new_df["_end8"].tolist()))
    if current_df is not None and len(current_df) > 0:
        current_df = current_df.copy()
        current_df["_end8"] = current_df["end_date"].astype(str).str.replace("-", "").str[:8]
        keep = ~current_df.apply(lambda r: (r["ts_code"], r["_end8"]) in keys_new, axis=1)
        current_df = current_df.loc[keep].drop(columns=["_end8"], errors="ignore")
        result = pd.concat([current_df, new_df.drop(columns=["_end8"], errors="ignore")], ignore_index=True)
    else:
        result = new_df.drop(columns=["_end8"], errors="ignore")
    result = result[[c for c in cols if c in result.columns]].copy()
    result = result.drop_duplicates(subset=["ts_code", "end_date"], keep="last")
    result.to_csv(out_path, index=False, encoding="utf-8-sig")
    return result


def step2_financial_data(pro, stock_list, report_periods):
    """
    拉取财务指标，输出与 xtquant 版一致的列名。
    若 data/fina_indicator_pool.csv 已存在，则已有 (ts_code, 报告期) 跳过请求，只拉缺失的，再合并写回。
    report_periods: 单期字符串如 "20241231" 或 多期列表如 ["20241231","20231231","20221231"]。
    """
    if isinstance(report_periods, str):
        report_periods = [report_periods]
    period_label = ",".join(report_periods[:3]) + ("..." if len(report_periods) > 3 else "")
    out_path = os.path.join(DATA_DIR, "fina_indicator_pool.csv")

    # 已有数据：加载并构建 (ts_code, end_date_8) 集合，用于跳过已下载
    existing_df = None
    existing_keys = set()
    if os.path.exists(out_path):
        try:
            existing_df = pd.read_csv(out_path, dtype={"ts_code": str, "end_date": str}, encoding="utf-8-sig")
            if "ts_code" in existing_df.columns and "end_date" in existing_df.columns:
                end8 = existing_df["end_date"].astype(str).str.replace("-", "").str.strip().str[:8]
                for _, r in existing_df[["ts_code"]].assign(_e=end8).iterrows():
                    existing_keys.add((r["ts_code"], r["_e"]))
        except Exception:
            existing_df = None
            existing_keys = set()
    if existing_keys:
        print(f"\n[Step 2/3] 已存在 {len(existing_keys)} 条记录，仅拉取缺失的 (股票, 报告期)...")

    # 仅对未存在的 (ts_code, period) 发起请求
    to_fetch = []
    for period in report_periods:
        p8 = str(period).replace("-", "")[:8]
        for ts_code in stock_list:
            if (ts_code, p8) not in existing_keys:
                to_fetch.append((period, ts_code))

    total_all = len(stock_list) * len(report_periods)
    total_fetch = len(to_fetch)
    global _api_error_printed
    _api_error_printed.clear()
    cols = ["ts_code", "end_date", "roe", "bps", "eps", "debt_to_assets", "ocf_to_profit", "netprofit_yoy"]

    if total_fetch == 0:
        print(f"\n[Step 2/3] 拉取财务指标（报告期 {period_label}）：全部已存在，跳过 API 请求")
        result = existing_df
        if result is not None and len(result) > 0:
            print(f"  已保存 {result['ts_code'].nunique()} 只股票、{len(result)} 条 -> {out_path}")
        else:
            print("  当前无数据")
            return pd.DataFrame() if existing_df is None else existing_df

    print(f"\n[Step 2/3] 拉取财务指标（报告期 {period_label}）：需请求 {total_fetch}/{total_all}（跳过 {total_all - total_fetch}），每 {BATCH_SIZE} 条合并保存；节流约 500 次/分钟...")

    result = existing_df
    total_ok = 0
    total_fail = 0
    num_batches = (total_fetch + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_idx in range(num_batches):
        start = batch_idx * BATCH_SIZE
        batch = to_fetch[start:start + BATCH_SIZE]
        with _batch_error_lock:
            _batch_error_types.clear()
        batch_records = []
        batch_size = len(batch)
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            futures = {executor.submit(_fetch_one_fina, pro, period, ts_code): (period, ts_code) for period, ts_code in batch}
            done = 0
            for future in as_completed(futures):
                rec = future.result()
                if rec is not None:
                    batch_records.append(rec)
                done += 1
                if done % 100 == 0 or done == batch_size:
                    print(f"  批 {batch_idx + 1}/{num_batches} 进度 {done}/{batch_size}...")
        n_ok = len(batch_records)
        n_fail = batch_size - n_ok
        total_ok += n_ok
        total_fail += n_fail

        with _batch_error_lock:
            n_limit = _batch_error_types.count("limit")
            n_other = len(_batch_error_types) - n_limit
        if n_fail > 0:
            if n_limit > 0:
                print(f"  本批失败原因: 限频 {n_limit} 次，接口无数据或其它 {n_fail - n_limit} 次")
            else:
                print(f"  本批失败原因: 均为该报告期接口无数据（未返回记录）")

        current = pd.DataFrame()
        if os.path.exists(out_path):
            try:
                current = pd.read_csv(out_path, dtype={"ts_code": str, "end_date": str}, encoding="utf-8-sig")
            except Exception:
                current = result if result is not None and len(result) > 0 else pd.DataFrame()
        else:
            current = result if result is not None and len(result) > 0 else pd.DataFrame()
        result = _merge_and_save_fina(out_path, current, batch_records, cols)
        print(f"  批 {batch_idx + 1}/{num_batches} 已合并保存，本批成功 {n_ok} 失败 {n_fail}，当前共 {len(result)} 条 -> {out_path}")

    if total_fail > 0:
        print(f"  合计: 成功 {total_ok}，失败 {total_fail}（失败多为该报告期无数据或接口限频，若有 [API] 报错见上方）")

    print("\n  [数据校验] 贵州茅台(600519.SH)：")
    mt = result[result["ts_code"] == "600519.SH"]
    if len(mt) > 0:
        r = mt.iloc[0]
        print(f"    {r['end_date']}: roe={r.get('roe')}, debt_to_assets={r.get('debt_to_assets')}, bps={r.get('bps')}")
    else:
        print("    无数据")
    return result


# ================================================================
# Step 2b：经营现金流/净利润（ocf_to_profit），供 11 现金流/利润条件使用
# ================================================================
def step2b_ocf_to_profit(pro, fina_df):
    """
    用 Tushare 现金流量表与利润表计算 经营现金流/净利润，写回 fina_df。
    若具备 VIP 权限则按报告期批量拉取 cashflow_vip/income_vip，否则按股票补拉（请求量较大）。
    若无权限或失败则保留 ocf_to_profit 为空。
    """
    if fina_df is None or len(fina_df) == 0:
        return fina_df
    periods = fina_df["end_date"].astype(str).str.replace("-", "").str[:8].unique().tolist()
    if not periods:
        return fina_df

    # 尝试 VIP 按报告期全市场拉取（每期 2 次请求）
    ocf_list = []
    for period in periods:
        period8 = str(period)[:8]
        try:
            cf = getattr(pro, "cashflow_vip", None)
            inc = getattr(pro, "income_vip", None)
            if cf is None or inc is None:
                break
            df_cf = cf(period=period8, fields="ts_code,end_date,n_cashflow_act,report_type")
            df_inc = inc(period=period8, fields="ts_code,end_date,n_income,n_income_attr_p,report_type")
            if df_cf is None or len(df_cf) == 0 or df_inc is None or len(df_inc) == 0:
                continue
            # 合并报表 report_type=1
            df_cf = df_cf[df_cf.get("report_type", 1) == 1].drop_duplicates(subset=["ts_code", "end_date"], keep="last")
            df_inc = df_inc[df_inc.get("report_type", 1) == 1].drop_duplicates(subset=["ts_code", "end_date"], keep="last")
            df_cf["end8"] = df_cf["end_date"].astype(str).str.replace("-", "").str[:8]
            df_inc["end8"] = df_inc["end_date"].astype(str).str.replace("-", "").str[:8]
            merge = df_cf.merge(
                df_inc,
                on=["ts_code", "end8"],
                how="inner",
                suffixes=("", "_inc")
            )
            # 净利润优先用 n_income_attr_p（归属母公司），缺则用 n_income
            merge["n_income_use"] = merge.get("n_income_attr_p", merge.get("n_income"))
            merge["ocf_to_profit"] = merge["n_cashflow_act"] / merge["n_income_use"].replace(0, float("nan"))
            ocf_list.append(merge[["ts_code", "end8", "ocf_to_profit"]])
        except Exception as e:
            print(f"  [Step 2b] 报告期 {period8} 拉取现金流/利润失败: {e}")
            continue

    if not ocf_list:
        print("  [Step 2b] 未获取到现金流/利润数据（需 VIP 或按股票补拉），ocf_to_profit 保持为空")
        return fina_df

    ocf_df = pd.concat(ocf_list, ignore_index=True).rename(columns={"end8": "_end8"})
    fina_df = fina_df.copy()
    fina_df["_end8"] = fina_df["end_date"].astype(str).str.replace("-", "").str[:8]
    fina_df = fina_df.drop(columns=["ocf_to_profit"], errors="ignore")
    fina_df = fina_df.merge(ocf_df[["ts_code", "_end8", "ocf_to_profit"]], on=["ts_code", "_end8"], how="left")
    fina_df.drop(columns=["_end8"], inplace=True, errors="ignore")
    n_filled = fina_df["ocf_to_profit"].notna().sum()
    print(f"  [Step 2b] 已填充 ocf_to_profit：{n_filled} 条")
    out_path = os.path.join(DATA_DIR, "fina_indicator_pool.csv")
    fina_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    return fina_df


# ================================================================
# Step 3：指定日行情与估值（daily_basic）
# ================================================================
def step3_latest_prices(pro, stock_list, fina_df):
    """获取指定交易日行情，与 fina 合并得到 PB/PE（与 xtquant 版列一致）"""
    print(f"\n[Step 3/3] 获取 {TRADE_DATE} 行情与估值...")

    try:
        df = pro.daily_basic(
            trade_date=TRADE_DATE,
            fields="ts_code,trade_date,close,pe,pb,total_mv"
        )
    except Exception as e:
        print(f"  请求失败: {e}")
        return pd.DataFrame()

    if df is None or len(df) == 0:
        print("  该日无行情数据，请换 trade_date 或检查权限")
        return pd.DataFrame()

    df = df[df["ts_code"].isin(stock_list)].copy()
    df["trade_date"] = df["trade_date"].astype(str)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["total_mv"] = pd.to_numeric(df["total_mv"], errors="coerce")
    df["pe"] = pd.to_numeric(df["pe"], errors="coerce")
    df["pb"] = pd.to_numeric(df["pb"], errors="coerce")

    # 与财务最新 BPS/EPS 合并（若 daily_basic 无 pb/pe 可自行算）
    if len(fina_df) > 0:
        latest_fina = (
            fina_df.sort_values("end_date")
            .drop_duplicates(subset="ts_code", keep="last")[["ts_code", "bps", "eps"]]
            .copy()
        )
        df = df.merge(latest_fina, on="ts_code", how="left")
        mask_bps = df["bps"].notna() & (df["bps"] > 0)
        df.loc[mask_bps, "pb"] = (df.loc[mask_bps, "close"] / df.loc[mask_bps, "bps"]).round(3)
        mask_eps = df["eps"].notna() & (df["eps"] > 0)
        df.loc[mask_eps, "pe"] = (df.loc[mask_eps, "close"] / df.loc[mask_eps, "eps"]).round(2)

    keep = ["ts_code", "trade_date", "close", "pb", "pe", "total_mv"]
    daily_df = df[[c for c in keep if c in df.columns]].copy()
    daily_df["close"] = daily_df["close"].round(2)
    daily_df["total_mv"] = daily_df["total_mv"].round(2)

    out_path = os.path.join(DATA_DIR, "daily_basic_latest.csv")
    daily_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"  已保存 {len(daily_df)} 只 -> {out_path}")

    mt = daily_df[daily_df["ts_code"] == "600519.SH"]
    if len(mt) > 0:
        r = mt.iloc[0]
        print(f"  [校验] 贵州茅台: close={r['close']}, pb={r.get('pb')}, pe={r.get('pe')}, total_mv={r.get('total_mv')}")
    return daily_df


# ================================================================
# 主流程
# ================================================================
def run_download():
    if USE_MULTIPLE_PERIODS:
        report_periods = get_report_periods_annual(NUM_ANNUAL_PERIODS)
        report_label = ",".join(report_periods)
    else:
        report_period = get_latest_report_period() if REPORT_USE_LATEST else REPORT_PERIOD_FIXED
        report_periods = report_period
        report_label = report_period
    print("=" * 60)
    print("基本面选股 -- 数据下载（Tushare 版）")
    print("=" * 60)
    print(f"保存目录: {DATA_DIR}")
    print(f"基准交易日: {TRADE_DATE}  报告期: {report_label}" + (" (多期年报)" if USE_MULTIPLE_PERIODS else (" (最近报告期)" if REPORT_USE_LATEST else " (固定)")))
    print("=" * 60)

    try:
        pro = get_pro()
    except RuntimeError as e:
        print(e)
        return

    stock_df = step1_stock_info(pro)
    if stock_df is None or len(stock_df) == 0:
        print("错误: 无法获取股票列表")
        return

    stock_list = stock_df["ts_code"].tolist()
    fina_df = step2_financial_data(pro, stock_list, report_periods)
    fina_df = step2b_ocf_to_profit(pro, fina_df)
    daily_df = step3_latest_prices(pro, stock_list, fina_df)

    print("\n" + "=" * 60)
    print("数据下载完成")
    print("=" * 60)
    for fname in ["stock_basic.csv", "daily_basic_latest.csv", "fina_indicator_pool.csv"]:
        fpath = os.path.join(DATA_DIR, fname)
        if os.path.exists(fpath):
            print(f"  {fname:<30s}  {os.path.getsize(fpath) / 1024:.0f} KB")
    print("=" * 60)


if __name__ == "__main__":
    run_download()
