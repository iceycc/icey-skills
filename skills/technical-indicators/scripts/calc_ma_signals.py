# -*- coding: utf-8 -*-
"""
CASE：贵州茅台MA交易信号

- MA 为过去 N 日收盘价的平均，相当于市场成本线（低通滤波）
- 金叉：短周期上穿长周期，短期力量强于长期，趋势启动
- 死叉：短周期下穿长周期，趋势转弱

运行前请确保 data/600519_SH_daily.csv 存在。
"""
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'STHeiti', 'SimHei', 'Microsoft YaHei', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
import argparse


def load_stock_data(data_file):
    if not os.path.exists(data_file):
        print(f"错误：数据文件不存在 {data_file}")
        return None
    df = pd.read_csv(data_file, encoding='utf-8-sig')
    df['date'] = pd.to_datetime(df['date'])
    if 'close' not in df.columns:
        print("错误：数据缺少 close 列")
        return None
    df = df.sort_values('date').reset_index(drop=True)
    return df


def calc_ma_signals(data_file, stock_name=None, stock_code=None, ma_short=5, ma_long=20, show_days=120, output_dir=None):
    """
    计算MA移动平均线交易信号
    
    参数:
        data_file: 数据文件路径
        stock_name: 股票名称，可选
        stock_code: 股票代码，可选
        ma_short: 短期均线周期
        ma_long: 长期均线周期
        show_days: 展示最近N天的数据
        output_dir: 输出目录，默认为当前目录下的 outputs 文件夹
    
    返回:
        输出文件路径，失败返回 None
    """
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), 'outputs')
    
    # 从文件名推断股票代码和名称
    if stock_code is None:
        basename = os.path.basename(data_file)
        if '_daily.csv' in basename:
            stock_code = basename.replace('_daily.csv', '').replace('_', '.')
    
    if stock_name is None:
        stock_name = stock_code if stock_code else '股票'
    
    df = load_stock_data(data_file)
    if df is None:
        return None

    df = df.tail(show_days + ma_long).reset_index(drop=True)
    close = df['close'].values
    dates = pd.DatetimeIndex(df['date'])

    ma5 = pd.Series(close).rolling(ma_short, min_periods=1).mean().values
    ma20 = pd.Series(close).rolling(ma_long, min_periods=1).mean().values

    # 金叉：前一日 ma5 <= ma20，当日 ma5 > ma20
    # 死叉：前一日 ma5 >= ma20，当日 ma5 < ma20
    golden = []
    death = []
    for i in range(ma_long, len(close)):
        if ma5[i - 1] <= ma20[i - 1] and ma5[i] > ma20[i]:
            golden.append((i, dates[i], close[i]))
        if ma5[i - 1] >= ma20[i - 1] and ma5[i] < ma20[i]:
            death.append((i, dates[i], close[i]))

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(dates, close, 'b-', linewidth=1.2, label='收盘价')
    ax.plot(dates, ma5, 'orange', linewidth=1.2, label=f'MA{ma_short}')
    ax.plot(dates, ma20, 'green', linewidth=1.2, label=f'MA{ma_long}')

    for idx, dt, pr in golden:
        ax.scatter([dt], [pr], marker='^', color='red', s=100, zorder=5)
        ax.annotate('金叉', (dt, pr), textcoords='offset points', xytext=(0, 12), ha='center', fontsize=9, color='red')
    for idx, dt, pr in death:
        ax.scatter([dt], [pr], marker='v', color='green', s=100, zorder=5)
        ax.annotate('死叉', (dt, pr), textcoords='offset points', xytext=(0, -15), ha='center', fontsize=9, color='green')

    ax.set_ylabel('价格 (元)', fontsize=11)
    ax.set_xlabel('日期', fontsize=11)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    title = f'{stock_name}({stock_code}) MA{ma_short}/MA{ma_long} 金叉死叉' if stock_code else f'{stock_name} MA{ma_short}/MA{ma_long} 金叉死叉'
    ax.set_title(title, fontsize=12)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    plt.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    filename = f'{stock_code.replace(".", "_")}_ma_signals.png' if stock_code else 'ma_signals.png'
    out_path = os.path.join(output_dir, filename)
    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"图表已保存：{out_path}")
    if matplotlib.get_backend().lower() != 'agg':
        plt.show()

    print(f"\n本区间金叉次数：{len(golden)}，死叉次数：{len(death)}")
    print("说明：金叉偏多、死叉偏空；回踩 MA20 不破可视为支撑。")
    
    return out_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MA移动平均线交易信号计算工具')
    parser.add_argument('--data-file', type=str, required=True, help='数据文件路径')
    parser.add_argument('--stock-name', type=str, default=None, help='股票名称，可选')
    parser.add_argument('--stock-code', type=str, default=None, help='股票代码，可选')
    parser.add_argument('--ma-short', type=int, default=5, help='短期均线周期')
    parser.add_argument('--ma-long', type=int, default=20, help='长期均线周期')
    parser.add_argument('--show-days', type=int, default=120, help='展示最近N天的数据')
    parser.add_argument('--output-dir', type=str, default=None, help='输出目录，默认为当前目录下的 outputs 文件夹')
    
    args = parser.parse_args()
    
    calc_ma_signals(
        data_file=args.data_file,
        stock_name=args.stock_name,
        stock_code=args.stock_code,
        ma_short=args.ma_short,
        ma_long=args.ma_long,
        show_days=args.show_days,
        output_dir=args.output_dir
    )
