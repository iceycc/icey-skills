# -*- coding: utf-8 -*-
"""
CASE：获取财务指标

- 市值(Market Cap)：股价 * 总股本，把公司整个买下来要花多少钱
- PE(市盈率)：市值/净利润 = 股价/EPS，回本需要多少年
- PB(市净率)：股价/每股净资产，破产了还能剩多少

本脚本使用 Tushare daily_basic 接口获取真实基本面数据（需环境变量 TUSHARE_TOKEN ）。
同时用本地数据文件最后一日作为基准日期；若需与 Tushare 收盘价一致，
可直接采用 daily_basic 返回的 close。
"""
import os
import re
import argparse
import pandas as pd


def infer_stock_code_from_filename(data_file):
    """从文件名推断股票代码，例如：600519_SH_daily.csv -> 600519.SH"""
    if not data_file:
        return None
    basename = os.path.basename(data_file)
    # 匹配模式：数字_字母数字_daily.csv 或类似格式
    match = re.search(r'(\d{6})[_\-](\w+)', basename)
    if match:
        code = match.group(1)
        market = match.group(2).upper()
        # 处理市场后缀
        if market.startswith('SH') or market.startswith('SZ'):
            market = market[:2]
        elif market.startswith('HK'):
            market = 'HK'
        return f"{code}.{market}"
    return None


def load_last_trade_date_from_csv(data_file):
    """从本地 CSV 取最后交易日，用于与 Tushare 对齐日期"""
    if not os.path.exists(data_file):
        return None, None
    df = pd.read_csv(data_file, encoding='utf-8-sig')
    df['date'] = pd.to_datetime(df['date'])
    if 'close' not in df.columns or len(df) == 0:
        return None, None
    df = df.sort_values('date').reset_index(drop=True)
    last = df.iloc[-1]
    date_str = pd.Timestamp(last['date']).strftime('%Y%m%d')
    return date_str, float(last['close'])


def fetch_daily_basic(ts_code, trade_date):
    """调用 Tushare daily_basic 获取指定日期的每日指标（PE、PB、总股本、总市值等）"""
    token = os.environ.get('TUSHARE_TOKEN')
    if not token or not token.strip():
        print("错误：未设置环境变量 TUSHARE_TOKEN")
        return None
    try:
        import tushare as ts
        ts.set_token(token.strip())
        pro = ts.pro_api()
        pro._DataApi__token = token # 保证有这个代码，不然不可以获取
        pro._DataApi__http_url = 'http://lianghua.nanyangqiankun.top'  # 保证有这个代码，不然不可以获取
        pro._DataApi__token = token # 保证有这个代码，不然不可以获取
        pro._DataApi__http_url = 'http://lianghua.nanyangqiankun.top'  # 保证有这个代码，不然不可以获取
        df = pro.daily_basic(
            ts_code=ts_code,
            trade_date=trade_date,
            fields='ts_code,trade_date,close,pe,pb,total_share,total_mv,float_share,circ_mv'
        )
        if df is None or len(df) == 0:
            return None
        return df.iloc[0]
    except Exception as e:
        print(f"Tushare 请求失败：{e}")
        return None


def fetch_daily_basic_latest(ts_code, end_date, days_back=60):
    """若指定日无数据，则取 end_date 之前最近一段日期的最后一条"""
    token = os.environ.get('TUSHARE_TOKEN')
    if not token or not token.strip():
        return None
    try:
        import tushare as ts
        ts.set_token(token.strip())
        pro = ts.pro_api()
        pro._DataApi__token = token # 保证有这个代码，不然不可以获取
        pro._DataApi__http_url = 'http://lianghua.nanyangqiankun.top'  # 保证有这个代码，不然不可以获取
        end_d = pd.Timestamp(end_date)
        start_d = end_d - pd.Timedelta(days=days_back)
        start_date = start_d.strftime('%Y%m%d')
        df = pro.daily_basic(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields='ts_code,trade_date,close,pe,pb,total_share,total_mv,float_share,circ_mv'
        )
        if df is None or len(df) == 0:
            return None
        df = df.sort_values('trade_date').reset_index(drop=True)
        return df.iloc[-1]
    except Exception as e:
        print(f"Tushare 请求失败：{e}")
        return None


def run_demo(stock_code=None, stock_name=None, data_file=None):
    """
    运行财务指标获取演示
    
    参数:
        stock_code: 股票代码（如：600519.SH）
        stock_name: 股票名称
        data_file: 数据文件路径（CSV格式），用于获取最后交易日
    """
    # 从文件名推断股票代码（如果未提供）
    if data_file and not stock_code:
        stock_code = infer_stock_code_from_filename(data_file)
    
    # 设置默认值
    if not stock_code:
        stock_code = '600519.SH'
    if not data_file:
        data_file = os.path.join(os.getcwd(), 'data', f'{stock_code.replace(".", "_")}_daily.csv')
    if not stock_name:
        stock_name = stock_code
    
    # 基准日期与本地收盘价（用于展示；若 Tushare 有 close 则优先用 Tushare）
    trade_date_str, local_close = load_last_trade_date_from_csv(data_file)
    if trade_date_str is None:
        print("错误：无法从本地 CSV 获取最后交易日，请先下载数据")
        return

    row = fetch_daily_basic(stock_code, trade_date_str)
    if row is None:
        row = fetch_daily_basic_latest(stock_code, trade_date_str)
    if row is None:
        print("错误：Tushare 未返回该日基本面数据（daily_basic 需一定积分权限），请检查 TUSHARE_TOKEN 与积分")
        return

    # daily_basic: total_share 万股, total_mv 万元, close 元, pe, pb
    price = float(row.get('close', local_close))
    if pd.isna(price) or price <= 0:
        price = local_close
    trade_date = str(row.get('trade_date', trade_date_str))
    date_display = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"

    total_share_wan = float(row.get('total_share', 0))
    total_mv_wan = float(row.get('total_mv', 0))
    pe_raw = row.get('pe')
    pb_raw = row.get('pb')

    # 总股本：万股 -> 股
    total_shares = total_share_wan * 10000 if total_share_wan and total_share_wan > 0 else None
    # 总市值：万元 -> 亿元（展示用）；也可 股价*总股本 验证
    total_mv_yi = total_mv_wan / 10000 if total_mv_wan and total_mv_wan > 0 else None
    market_cap = price * total_shares if total_shares else (total_mv_wan * 10000 if total_mv_wan else None)

    pe = float(pe_raw) if pe_raw is not None and not (isinstance(pe_raw, float) and pd.isna(pe_raw)) else None
    pb = float(pb_raw) if pb_raw is not None and not (isinstance(pb_raw, float) and pd.isna(pb_raw)) else None

    # EPS = 股价 / PE, BPS = 股价 / PB
    eps = (price / pe) if pe and pe > 0 else None
    bps = (price / pb) if pb and pb > 0 else None

    print(f"股票：{stock_name}({stock_code})")
    print(f"数据来源：Tushare daily_basic（真实数据）")
    print(f"基准日期：{date_display}")
    print(f"收盘价：{price:.2f} 元")
    if total_shares:
        print(f"总股本：{total_shares / 1e8:.2f} 亿股")
    if total_mv_yi is not None:
        print(f"总市值（Tushare）：{total_mv_yi:.2f} 亿元")
    if eps is not None:
        print(f"每股收益(EPS)：{eps:.2f} 元（由 股价/PE 反推）")
    if bps is not None:
        print(f"每股净资产(BPS)：{bps:.2f} 元（由 股价/PB 反推）")
    print("-" * 60)
    if total_shares and market_cap is not None:
        print(f"市值 = 股价 * 总股本 = {price:.2f} * {total_shares/1e8:.2f}亿 = {market_cap/1e8:.2f} 亿元")
    elif total_mv_yi is not None:
        print(f"总市值：{total_mv_yi:.2f} 亿元（Tushare）")
    if pe is not None:
        print(f"PE(市盈率) = {pe:.2f} （约{pe:.0f}年回本）")
    if pb is not None:
        print(f"PB(市净率) = {pb:.2f}")
    print("-" * 60)
    print("说明：PE 越低越便宜，但成长股可容忍高 PE；PB<1 为破净，常见于银行、钢铁。")
    print("=" * 60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='获取财务指标')
    parser.add_argument('--stock-code', type=str, default=None, help='股票代码（如：600519.SH）')
    parser.add_argument('--stock-name', type=str, default=None, help='股票名称')
    parser.add_argument('--data-file', type=str, default=None, help='数据文件路径（CSV格式），用于获取最后交易日')
    
    args = parser.parse_args()
    
    # 如果提供了data_file但未提供stock_code，尝试从文件名推断
    if args.data_file and not args.stock_code:
        inferred_code = infer_stock_code_from_filename(args.data_file)
        if inferred_code:
            args.stock_code = inferred_code
    
    run_demo(
        stock_code=args.stock_code,
        stock_name=args.stock_name,
        data_file=args.data_file
    )
