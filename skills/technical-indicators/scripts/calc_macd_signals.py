# -*- coding: utf-8 -*-
"""
CASE：MACD交易信号
- MACD 衡量短期与长期均线的距离，即动量
- 红柱变长：上涨加速；红柱变短（背驰）：涨速放缓，需警惕
- 金叉做多、死叉做空

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
    if 'close' not in df.columns:
        return None
    df = df.sort_values('date').reset_index(drop=True)
    return df


def get_MACD(close, short=12, long=26, m=9):
    ema_short = pd.Series(close).ewm(span=short, adjust=False).mean()
    ema_long = pd.Series(close).ewm(span=long, adjust=False).mean()
    dif = ema_short - ema_long
    dea = dif.ewm(span=m, adjust=False).mean()
    macd_bar = (dif - dea) * 2
    return dif.values, dea.values, macd_bar.values


def run_demo(data_file=None, stock_name=None, stock_code=None, short_period=12, long_period=26, signal_period=9, show_days=150):
    """
    运行MACD交易信号演示
    
    参数:
        data_file: 数据文件路径
        stock_name: 股票名称
        stock_code: 股票代码
        short_period: MACD短期周期，默认12
        long_period: MACD长期周期，默认26
        signal_period: MACD信号周期，默认9
        show_days: 显示天数，默认150
    """
    # 从文件名推断股票代码（如果未提供）
    if data_file and not stock_code:
        stock_code = infer_stock_code_from_filename(data_file)
    
    # 设置默认值
    if not data_file:
        data_file = os.path.join(os.getcwd(), 'data', '600519_SH_daily.csv')
    if not stock_name:
        stock_name = stock_code if stock_code else '股票'
    if not stock_code:
        stock_code = '600519.SH'
    
    df = load_stock_data(data_file)
    if df is None:
        return

    df = df.tail(show_days + long_period + signal_period).reset_index(drop=True)
    close = df['close'].values
    dates = pd.DatetimeIndex(df['date'])

    dif, dea, macd_bar = get_MACD(close, short_period, long_period, signal_period)

    golden = []
    death = []
    for i in range(1, len(dif)):
        if dif[i - 1] <= dea[i - 1] and dif[i] > dea[i]:
            golden.append((i, dates[i], close[i]))
        if dif[i - 1] >= dea[i - 1] and dif[i] < dea[i]:
            death.append((i, dates[i], close[i]))

    # 找一次「红柱缩短」背驰：红柱阶段，前一日柱更长
    divergence_candidates = []
    for i in range(2, len(macd_bar)):
        if macd_bar[i] > 0 and macd_bar[i - 1] > 0 and macd_bar[i] < macd_bar[i - 1]:
            divergence_candidates.append((i, dates[i], close[i], macd_bar[i]))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    ax1.plot(dates, close, 'b-', linewidth=1.2, label='收盘价')
    for _, dt, pr in golden:
        ax1.scatter([dt], [pr], marker='^', color='red', s=80, zorder=5)
        ax1.annotate('金叉', (dt, pr), textcoords='offset points', xytext=(0, 10), ha='center', fontsize=8, color='red')
    for _, dt, pr in death:
        ax1.scatter([dt], [pr], marker='v', color='green', s=80, zorder=5)
        ax1.annotate('死叉', (dt, pr), textcoords='offset points', xytext=(0, -12), ha='center', fontsize=8, color='green')
    ax1.set_ylabel('价格 (元)')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_title('收盘价与买卖点')

    ax2.plot(dates, dif, 'b-', linewidth=1, label='DIF')
    ax2.plot(dates, dea, 'orange', linewidth=1, label='DEA')
    colors = ['red' if v >= 0 else 'green' for v in macd_bar]
    ax2.bar(dates, macd_bar, color=colors, alpha=0.6, width=1.5)
    ax2.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
    ax2.set_ylabel('MACD')
    ax2.set_xlabel('日期')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.set_title(f'MACD({short_period},{long_period},{signal_period}) 红柱变短=背驰，需警惕', fontsize=11)

    ax2.xaxis.set_major_locator(mdates.MonthLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    plt.tight_layout()

    out_dir = os.path.join(os.getcwd(), 'outputs')
    os.makedirs(out_dir, exist_ok=True)
    out_filename = f'{stock_name}MACD交易信号.png' if stock_name else 'MACD交易信号.png'
    out_path = os.path.join(out_dir, out_filename)
    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"图表已保存：{out_path}")
    if matplotlib.get_backend().lower() != 'agg':
        plt.show()

    print(f"\n本区间金叉 {len(golden)} 次，死叉 {len(death)} 次")
    print("课程要点：红柱变短为背驰，涨速放缓，量化中常用作风险信号。")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MACD交易信号分析')
    parser.add_argument('--data-file', type=str, default=None, help='数据文件路径（CSV格式）')
    parser.add_argument('--stock-name', type=str, default=None, help='股票名称')
    parser.add_argument('--stock-code', type=str, default=None, help='股票代码（如：600519.SH）')
    parser.add_argument('--short-period', type=int, default=12, help='MACD短期周期，默认12')
    parser.add_argument('--long-period', type=int, default=26, help='MACD长期周期，默认26')
    parser.add_argument('--signal-period', type=int, default=9, help='MACD信号周期，默认9')
    parser.add_argument('--show-days', type=int, default=150, help='显示天数，默认150')
    
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
        short_period=args.short_period,
        long_period=args.long_period,
        signal_period=args.signal_period,
        show_days=args.show_days
    )
