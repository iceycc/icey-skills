# -*- coding: utf-8 -*-
"""
Tushare 分钟数据下载（通用脚本）
股票代码、目标日期、频率、输出目录等通过命令行或函数参数传入。
依赖：pip install tushare，环境变量 TUSHARE_TOKEN。分钟数据需单独开通权限。
"""
import os
import traceback
import argparse
import pandas as pd
import tushare as ts

from tushare_pro import get_pro


def download_minute_data(
    stock_code,
    stock_name=None,
    target_date='20260210',
    freq='1min',
    output_dir=None,
):
    """
    下载指定日期的分钟 K 线并保存为 CSV。

    参数:
        stock_code: 股票代码，如 '600519.SH'
        stock_name: 股票名称，可选
        target_date: 目标日期，格式 YYYYMMDD
        freq: 频率，如 '1min', '5min', '15min', '30min', '60min'
        output_dir: 输出目录，默认当前目录下的 data

    返回:
        输出文件路径，失败返回 None
    """
    if stock_name is None:
        stock_name = stock_code
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), 'data')

    print(f"开始下载分钟数据（Tushare）")
    print(f"股票：{stock_name}({stock_code})  日期：{target_date}  频率：{freq}")
    print("-" * 60)

    try:
        print("步骤1：初始化 Tushare Pro...")
        pro = get_pro()

        print(f"\n步骤2：下载 {freq} 数据（前复权）...")
        df = ts.pro_bar(
            api=pro,
            ts_code=stock_code,
            start_date=target_date,
            end_date=target_date,
            adj='qfq',
            freq=freq,
        )

        if df is None or len(df) == 0:
            print("错误：无法获取分钟数据（可能未开通分钟权限或非交易日）")
            return None

        df = df.rename(columns={'trade_time': 'datetime', 'vol': 'volume'})
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        keep_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume', 'amount']
        df = df[[c for c in keep_cols if c in df.columns]]

        print(f"成功获取 {len(df)} 条分钟数据")
        print(f"时间范围：{df['datetime'].iloc[0]} 至 {df['datetime'].iloc[-1]}")

        print("\n步骤3：保存到 CSV...")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'{stock_code.replace(".", "_")}_1min_tushare.csv')
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"数据已保存至：{output_file}")
        return output_file

    except Exception as e:
        print(f"下载数据过程中发生错误：{e}")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tushare 分钟数据下载（参数由命令行传入）')
    parser.add_argument('--stock-code', type=str, required=True, help='股票代码，如 600519.SH')
    parser.add_argument('--stock-name', type=str, default=None)
    parser.add_argument('--target-date', type=str, default='20260210', help='目标日期 YYYYMMDD')
    parser.add_argument('--freq', type=str, default='1min', help='1min, 5min, 15min, 30min, 60min')
    parser.add_argument('--output-dir', type=str, default=None)
    args = parser.parse_args()

    result = download_minute_data(
        stock_code=args.stock_code,
        stock_name=args.stock_name,
        target_date=args.target_date,
        freq=args.freq,
        output_dir=args.output_dir,
    )
    if result:
        print("\n" + "=" * 60 + "\n分钟数据下载完成! 文件：" + result + "\n" + "=" * 60)
    else:
        print("\n分钟数据下载失败。")
