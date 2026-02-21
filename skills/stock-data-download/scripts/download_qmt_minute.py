# -*- coding: utf-8 -*-
"""
QMT 分钟数据下载（通用脚本）
股票代码、目标日期、周期、输出目录等通过命令行或函数参数传入。
依赖：QMT + xtquant，运行前需启动 miniQMT 客户端。
"""
import os
import time
import traceback
import argparse
import pandas as pd
from xtquant import xtdata


def download_minute_data(
    stock_code,
    stock_name=None,
    target_date='20260210',
    period='1m',
    output_dir=None,
):
    """
    下载指定日期的分钟 K 线并保存为 CSV。

    参数:
        stock_code: 股票代码，如 '600519.SH'
        stock_name: 股票名称，可选
        target_date: 目标日期，格式 YYYYMMDD
        period: K 线周期，如 '1m', '5m', '15m', '30m', '60m'
        output_dir: 输出目录，默认当前目录下的 data

    返回:
        输出文件路径，失败返回 None
    """
    if stock_name is None:
        stock_name = stock_code
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), 'data')

    #  end_time 设为目标日下一天
    from datetime import datetime, timedelta
    try:
        dt = datetime.strptime(target_date, '%Y%m%d') + timedelta(days=1)
        end_time = dt.strftime('%Y%m%d')
    except Exception:
        end_time = target_date

    print(f"开始下载分钟数据（QMT）")
    print(f"股票：{stock_name}({stock_code})  日期：{target_date}  周期：{period}")
    print("-" * 60)

    try:
        print("步骤1：连接 QMT 数据服务...")
        xtdata.connect()

        print("\n步骤2：下载分钟数据...")
        xtdata.download_history_data(
            stock_code=stock_code,
            period=period,
            start_time=target_date,
        )
        time.sleep(2)

        print("\n步骤3：获取分钟 K 线...")
        res = xtdata.get_market_data(
            stock_list=[stock_code],
            period=period,
            start_time=target_date,
            end_time=end_time,
            count=-1,
            dividend_type='front',
            fill_data=False,
        )

        if not res or 'close' not in res or stock_code not in res['close'].index:
            print("错误：无法获取分钟数据")
            return None

        close_df = res['close']
        open_df = res.get('open')
        high_df = res.get('high')
        low_df = res.get('low')
        volume_df = res.get('volume')
        amount_df = res.get('amount')
        timestamps = close_df.columns.tolist()

        data_dict = {'datetime': timestamps, 'close': close_df.loc[stock_code].values}
        if open_df is not None and stock_code in open_df.index:
            data_dict['open'] = open_df.loc[stock_code].values
        if high_df is not None and stock_code in high_df.index:
            data_dict['high'] = high_df.loc[stock_code].values
        if low_df is not None and stock_code in low_df.index:
            data_dict['low'] = low_df.loc[stock_code].values
        if volume_df is not None and stock_code in volume_df.index:
            data_dict['volume'] = volume_df.loc[stock_code].values
        if amount_df is not None and stock_code in amount_df.index:
            data_dict['amount'] = amount_df.loc[stock_code].values

        df = pd.DataFrame(data_dict)
        df['datetime'] = pd.to_datetime(df['datetime'].astype(str), format='%Y%m%d%H%M%S', errors='coerce')
        df = df.dropna(subset=['datetime', 'close'])
        target_dt = pd.Timestamp(target_date)
        df = df[df['datetime'].dt.date == target_dt.date()].sort_values('datetime').reset_index(drop=True)

        if len(df) == 0:
            print(f"警告：{target_date} 没有分钟数据（可能非交易日）")
            return None

        print(f"成功获取 {len(df)} 条分钟数据")
        print(f"时间范围：{df['datetime'].iloc[0]} 至 {df['datetime'].iloc[-1]}")

        print("\n步骤4：保存到 CSV...")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'{stock_code.replace(".", "_")}_1min_QMT.csv')
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"数据已保存至：{output_file}")
        return output_file

    except Exception as e:
        print(f"下载数据过程中发生错误：{e}")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='QMT 分钟数据下载（参数由命令行传入）')
    parser.add_argument('--stock-code', type=str, required=True, help='股票代码，如 600519.SH')
    parser.add_argument('--stock-name', type=str, default=None)
    parser.add_argument('--target-date', type=str, default='20260210', help='目标日期 YYYYMMDD')
    parser.add_argument('--period', type=str, default='1m', help='K线周期：1m, 5m, 15m, 30m, 60m')
    parser.add_argument('--output-dir', type=str, default=None)
    args = parser.parse_args()

    result = download_minute_data(
        stock_code=args.stock_code,
        stock_name=args.stock_name,
        target_date=args.target_date,
        period=args.period,
        output_dir=args.output_dir,
    )
    if result:
        print("\n" + "=" * 60 + "\n分钟数据下载完成! 文件：" + result + "\n" + "=" * 60)
    else:
        print("\n分钟数据下载失败。")
