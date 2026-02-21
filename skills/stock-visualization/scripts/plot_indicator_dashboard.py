# -*- coding: utf-8 -*-
"""
CASE：指标仪表盘
- 趋势型：MA、MACD，看方向
- 震荡型：RSI，看位置（山顶/山谷）
- 能量型：成交量，看燃料
- 波动型：ATR，看风险

运行前请确保数据文件存在。
"""
import os
import re
import argparse
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'STHeiti', 'SimHei', 'Microsoft YaHei', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


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
    for col in ['close', 'high', 'low', 'volume']:
        if col not in df.columns:
            print(f"错误：数据缺少 {col} 列")
            return None
    df = df.sort_values('date').reset_index(drop=True)
    return df


def calc_rsi(close, period=14):
    n = len(close)
    rsi = np.full(n, np.nan)
    if n < period + 1:
        return rsi
    gains = np.zeros(n)
    losses = np.zeros(n)
    for i in range(1, n):
        d = close[i] - close[i - 1]
        gains[i] = d if d > 0 else 0
        losses[i] = -d if d < 0 else 0
    avg_gain = np.mean(gains[1:period + 1])
    avg_loss = np.mean(losses[1:period + 1])
    for i in range(period, n):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - 100.0 / (1.0 + rs)
    return rsi


def calc_atr(high, low, close, period=14):
    n = len(close)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    atr = pd.Series(tr).rolling(period, min_periods=period).mean().values
    return atr


def run_demo(data_file=None, stock_name=None, stock_code=None, show_days=80, ma_period=20, rsi_period=14, atr_period=14):
    """
    运行指标仪表盘演示
    
    参数:
        data_file: 数据文件路径
        stock_name: 股票名称
        stock_code: 股票代码
        show_days: 显示天数，默认80
        ma_period: MA周期，默认20
        rsi_period: RSI周期，默认14
        atr_period: ATR周期，默认14
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
    
    df = load_stock_data(data_file)
    if df is None:
        return

    df = df.tail(show_days + max(ma_period, rsi_period, atr_period) + 5).reset_index(drop=True)
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    volume = df['volume'].values
    dates = pd.DatetimeIndex(df['date'])

    ma20 = pd.Series(close).rolling(ma_period, min_periods=1).mean().values
    rsi = calc_rsi(close, rsi_period)
    atr = calc_atr(high, low, close, atr_period)

    valid = ~np.isnan(rsi) & ~np.isnan(atr)
    dates_v = dates[valid]
    close_v = close[valid]
    ma20_v = ma20[valid]
    rsi_v = rsi[valid]
    atr_v = atr[valid]
    volume_v = volume[valid]

    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    fig.suptitle(f'{stock_name}({stock_code}) 四维指标仪表盘：趋势+震荡+能量+波动', fontsize=14, fontweight='bold')

    axes[0].plot(dates_v, close_v, 'b-', linewidth=1.2, label='收盘价')
    axes[0].plot(dates_v, ma20_v, 'orange', linewidth=1.2, label=f'MA{ma_period}(趋势)')
    axes[0].set_ylabel('价格')
    axes[0].legend(loc='upper left', fontsize=9)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_title('趋势型：MA 方向', fontsize=10)

    axes[1].plot(dates_v, rsi_v, 'purple', linewidth=1.2, label=f'RSI({rsi_period})')
    axes[1].axhline(y=80, color='red', linestyle='--', alpha=0.7)
    axes[1].axhline(y=20, color='green', linestyle='--', alpha=0.7)
    axes[1].axhline(y=50, color='gray', linestyle=':', alpha=0.5)
    axes[1].set_ylim(0, 100)
    axes[1].set_ylabel('RSI')
    axes[1].legend(loc='upper left', fontsize=9)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_title('震荡型：RSI 位置(超买/超卖)', fontsize=10)

    colors = ['red' if close_v[i] >= (close_v[i - 1] if i > 0 else close_v[0]) else 'green' for i in range(len(dates_v))]
    axes[2].bar(dates_v, volume_v / 1e4, color=colors, alpha=0.7, width=0.8)
    axes[2].set_ylabel('成交量(万)')
    axes[2].set_title('能量型：成交量 燃料', fontsize=10)
    axes[2].grid(True, alpha=0.3, axis='y')

    axes[3].plot(dates_v, atr_v, 'brown', linewidth=1.2, label=f'ATR({atr_period})')
    axes[3].set_ylabel('ATR')
    axes[3].set_xlabel('日期')
    axes[3].legend(loc='upper left', fontsize=9)
    axes[3].grid(True, alpha=0.3)
    axes[3].set_title('波动型：ATR 风险', fontsize=10)

    plt.xticks(rotation=45)
    plt.tight_layout()

    out_dir = os.path.join(os.getcwd(), 'outputs')
    os.makedirs(out_dir, exist_ok=True)
    out_filename = f'9_{stock_name}指标仪表盘.png' if stock_name else '9_指标仪表盘.png'
    out_path = os.path.join(out_dir, out_filename)
    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"图表已保存：{out_path}")
    if matplotlib.get_backend().lower() != 'agg':
        plt.show()

    print("\n说明：不要用 MACD 和均线同时验证同一信号（同源）；应多维度：趋势+震荡+能量+波动。")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='指标仪表盘')
    parser.add_argument('--data-file', type=str, default=None, help='数据文件路径（CSV格式）')
    parser.add_argument('--stock-name', type=str, default=None, help='股票名称')
    parser.add_argument('--stock-code', type=str, default=None, help='股票代码（如：600519.SH）')
    parser.add_argument('--show-days', type=int, default=80, help='显示天数，默认80')
    parser.add_argument('--ma-period', type=int, default=20, help='MA周期，默认20')
    parser.add_argument('--rsi-period', type=int, default=14, help='RSI周期，默认14')
    parser.add_argument('--atr-period', type=int, default=14, help='ATR周期，默认14')
    
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
        show_days=args.show_days,
        ma_period=args.ma_period,
        rsi_period=args.rsi_period,
        atr_period=args.atr_period
    )
