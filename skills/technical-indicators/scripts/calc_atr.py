# -*- coding: utf-8 -*-
"""
CASE：ATR指标计算
- ATR(N)：取 N 日内的「真实波幅」的均值，真实波幅 = max(高-低, |高-前收|, |低-前收|)
- 风控：止损常用 2*ATR，跌穿正常波动则趋势坏
- 仓位：波动大的股票仓位要小，波动小的可适当加大

运行前请确保数据文件存在。
"""
import os
import re
import argparse
import pandas as pd
import numpy as np


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


def load_stock_data(data_file):
    if not os.path.exists(data_file):
        print(f"错误：数据文件不存在 {data_file}")
        return None
    df = pd.read_csv(data_file, encoding='utf-8-sig')
    df['date'] = pd.to_datetime(df['date'])
    for col in ['high', 'low', 'close']:
        if col not in df.columns:
            print(f"错误：数据缺少 {col} 列")
            return None
    df = df.sort_values('date').reset_index(drop=True)
    return df


def calc_atr(high, low, close, period=14):
    """真实波幅 TR = max(高-低, |高-前收|, |低-前收|)，ATR = TR 的 N 日均"""
    n = len(close)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1])
        )
    atr = pd.Series(tr).rolling(period, min_periods=period).mean().values
    return atr


def run_demo(data_file=None, stock_name=None, stock_code=None, atr_period=14, lookback_days=60):
    """
    运行ATR指标计算演示
    
    参数:
        data_file: 数据文件路径
        stock_name: 股票名称
        stock_code: 股票代码
        atr_period: ATR周期，默认14
        lookback_days: 回看天数，默认60
    """
    # 从文件名推断股票代码（如果未提供）
    if data_file and not stock_code:
        stock_code = infer_stock_code_from_filename(data_file)
    
    # 设置默认值
    if not data_file:
        data_file = os.path.join(os.getcwd(), 'data', '601899_SH_daily.csv')
    if not stock_name:
        stock_name = stock_code if stock_code else '股票'
    if not stock_code:
        stock_code = '601899.SH'
    
    df = load_stock_data(data_file)
    if df is None:
        return

    df = df.tail(lookback_days + atr_period).reset_index(drop=True)
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    dates = df['date'].values

    atr = calc_atr(high, low, close, atr_period)
    valid = ~np.isnan(atr)
    atr_valid = atr[valid]
    close_valid = close[valid]
    dates_valid = dates[valid]

    last_atr = atr_valid[-1]
    last_close = close_valid[-1]
    last_date = pd.Timestamp(dates_valid[-1]).strftime('%Y-%m-%d')
    stop_loss_price = last_close - 2 * last_atr

    print(f"股票：{stock_name}({stock_code})")
    print(f"ATR 周期：{atr_period} 日")
    print(f"最近一日：{last_date}")
    print(f"收盘价：{last_close:.2f} 元")
    print(f"ATR({atr_period})：{last_atr:.2f} 元（日均波动约 {last_atr:.2f} 元）")
    print(f"2*ATR 止损距离：{2 * last_atr:.2f} 元")
    print(f"若当日买入，2*ATR 止损价：{stop_loss_price:.2f} 元（跌破则考虑止损）")
    print("-" * 60)
    print("说明：波动大的标的仓位要小；止损常设为 2*ATR，海龟法则核心。")
    print("=" * 60)

    # 最近 5 日 ATR 与对应 2*ATR 止损价
    print("\n最近 5 日 ATR 与 2*ATR 止损价：")
    for i in range(-5, 0):
        d = pd.Timestamp(dates_valid[i]).strftime('%Y-%m-%d')
        c = close_valid[i]
        a = atr_valid[i]
        sl = c - 2 * a
        print(f"  {d}  收盘={c:.2f}  ATR={a:.2f}  2*ATR止损价={sl:.2f}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ATR指标计算')
    parser.add_argument('--data-file', type=str, default=None, help='数据文件路径（CSV格式）')
    parser.add_argument('--stock-name', type=str, default=None, help='股票名称')
    parser.add_argument('--stock-code', type=str, default=None, help='股票代码（如：601899.SH）')
    parser.add_argument('--atr-period', type=int, default=14, help='ATR周期，默认14')
    parser.add_argument('--lookback-days', type=int, default=60, help='回看天数，默认60')
    
    args = parser.parse_args()
    
    # 如果提供了data_file但未提供stock_code，尝试从文件名推断
    if args.data_file and not args.stock_code:
        inferred_code = infer_stock_code_from_filename(args.data_file)
        if inferred_code:
            args.stock_code = inferred_code
    
    run_demo(
        data_file=args.data_file,
        stock_name=args.stock_name,
        stock_code=args.stock_code,
        atr_period=args.atr_period,
        lookback_days=args.lookback_days
    )
