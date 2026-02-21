# -*- coding: utf-8 -*-
"""
CASE：RSI指标计算
- RSI 在 [0,100]，超过 80 为超买（太贵），低于 20 为超卖（太便宜）
- 量化解读：均值回归概率高；RSI<20 时反弹概率大，可作网格买入参考
- 本脚本计算 RSI，绘制价格与 RSI，并标注超买/超卖区间

运行前请确保数据文件存在
"""
import os
import re
import argparse
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 无图形界面时直接保存不阻塞；若需弹窗可注释本行
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
    """从CSV加载日线数据"""
    if not os.path.exists(data_file):
        print(f"错误：数据文件不存在 {data_file}")
        print("请先运行 1-qmt_download_data.py 下载数据")
        return None
    df = pd.read_csv(data_file, encoding='utf-8-sig')
    df['date'] = pd.to_datetime(df['date'])
    if 'close' not in df.columns:
        print("错误：数据缺少 close 列")
        return None
    df = df.sort_values('date').reset_index(drop=True)
    return df


def calc_rsi(close, period=14):
    """
    计算 RSI：RSI = 100 - 100/(1 + RS)，RS = 平均涨幅/平均跌幅
    使用 Wilder 平滑（Wilder's smoothing）
    """
    n = len(close)
    rsi = np.full(n, np.nan)
    if n < period + 1:
        return rsi

    gains = np.zeros(n)
    losses = np.zeros(n)
    for i in range(1, n):
        diff = close[i] - close[i - 1]
        if diff > 0:
            gains[i] = diff
        else:
            losses[i] = -diff

    # 第一段：前 period 日的平均涨跌
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


def run_demo(data_file=None, stock_name=None, stock_code=None, rsi_period=14, show_days=120, overbought=80, oversold=20):
    """
    运行RSI指标计算演示
    
    参数:
        data_file: 数据文件路径
        stock_name: 股票名称
        stock_code: 股票代码
        rsi_period: RSI周期，默认14
        show_days: 显示天数，默认120
        overbought: 超买阈值，默认80
        oversold: 超卖阈值，默认20
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

    df = df.tail(show_days + rsi_period + 5).reset_index(drop=True)
    close = df['close'].values
    dates = pd.DatetimeIndex(df['date'])

    rsi = calc_rsi(close, rsi_period)
    # 去掉前面无效的
    valid = ~np.isnan(rsi)
    dates = dates[valid]
    close = close[valid]
    rsi = rsi[valid]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle(f'{stock_name}({stock_code}) RSI({rsi_period}) 超买超卖示意', fontsize=14, fontweight='bold')

    # 子图1：收盘价
    ax1.plot(dates, close, 'b-', linewidth=1.2, label='收盘价')
    ax1.set_ylabel('价格 (元)', fontsize=11)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_title('收盘价', fontsize=11)

    # 子图2：RSI + 超买超卖线
    ax2.plot(dates, rsi, 'purple', linewidth=1.2, label=f'RSI({rsi_period})')
    ax2.axhline(y=overbought, color='red', linestyle='--', linewidth=1, alpha=0.8, label=f'超买 {overbought}')
    ax2.axhline(y=oversold, color='green', linestyle='--', linewidth=1, alpha=0.8, label=f'超卖 {oversold}')
    ax2.axhline(y=50, color='gray', linestyle=':', linewidth=0.8, alpha=0.6)
    ax2.fill_between(dates, overbought, 100, alpha=0.15, color='red')
    ax2.fill_between(dates, 0, oversold, alpha=0.15, color='green')
    ax2.set_ylim(0, 100)
    ax2.set_ylabel('RSI', fontsize=11)
    ax2.set_xlabel('日期', fontsize=11)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.set_title(f'RSI：>={overbought} 超买（考虑减仓/网格卖），<={oversold} 超卖（考虑加仓/网格买）', fontsize=11)

    # 标注超买超卖日
    oversold_dates = dates[rsi <= oversold]
    overbought_dates = dates[rsi >= overbought]
    if len(oversold_dates) > 0:
        ax2.scatter(oversold_dates, rsi[rsi <= oversold], color='green', s=40, zorder=5, label='超卖日')
    if len(overbought_dates) > 0:
        ax2.scatter(overbought_dates, rsi[rsi >= overbought], color='red', s=40, zorder=5, label='超买日')

    ax2.xaxis.set_major_locator(mdates.MonthLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    plt.tight_layout()

    # 统计
    print(f"\n本区间内 RSI<={oversold} 超卖天数: {np.sum(rsi <= oversold)}")
    print(f"本区间内 RSI>={overbought} 超买天数: {np.sum(rsi >= overbought)}")
    print("课程要点：RSI<20 时反弹概率大，可作为网格策略的买入参考；RSI>80 时可考虑减仓或网格卖出。")

    output_dir = os.path.join(os.getcwd(), 'outputs')
    os.makedirs(output_dir, exist_ok=True)
    out_filename = f'{stock_name}RSI指标计算.png' if stock_name else 'RSI指标计算.png'
    out_path = os.path.join(output_dir, out_filename)
    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"\n图表已保存：{out_path}")
    if matplotlib.get_backend().lower() != 'agg':
        plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RSI指标计算')
    parser.add_argument('--data-file', type=str, default=None, help='数据文件路径（CSV格式）')
    parser.add_argument('--stock-name', type=str, default=None, help='股票名称')
    parser.add_argument('--stock-code', type=str, default=None, help='股票代码（如：600519.SH）')
    parser.add_argument('--rsi-period', type=int, default=14, help='RSI周期，默认14')
    parser.add_argument('--show-days', type=int, default=120, help='显示天数，默认120')
    parser.add_argument('--overbought', type=int, default=80, help='超买阈值，默认80')
    parser.add_argument('--oversold', type=int, default=20, help='超卖阈值，默认20')
    
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
        rsi_period=args.rsi_period,
        show_days=args.show_days,
        overbought=args.overbought,
        oversold=args.oversold
    )
