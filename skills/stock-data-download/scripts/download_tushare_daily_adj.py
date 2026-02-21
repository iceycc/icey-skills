# -*- coding: utf-8 -*-
"""
Tushare 日线数据下载（前复权，复权脚本）
使用 ts.pro_bar 获取前复权日线，与 download_tushare_daily.py（历史/未复权）并存，不合并。
股票代码、时间区间、输出目录等通过命令行或函数参数传入。
"""
import os
import traceback
import argparse
import pandas as pd
import tushare as ts
from datetime import datetime

from tushare_pro import get_pro


def download_stock_data(
    stock_code,
    stock_name=None,
    start_date='20240101',
    end_date=None,
    output_dir=None,
    adj='qfq',
):
    """
    下载股票前复权日线并保存为 CSV。
    与 download_tushare_daily.py（pro.daily 历史数据）区分：本脚本为复权数据。

    参数:
        stock_code: 股票代码，如 '600519.SH'
        stock_name: 股票名称，可选
        start_date: 开始日期，格式 YYYYMMDD
        end_date: 结束日期，格式 YYYYMMDD，默认为今天
        output_dir: 输出目录，默认当前目录下的 data
        adj: 复权类型，'qfq' 前复权 / 'hfq' 后复权 / None 不复权

    返回:
        输出文件路径，失败返回 None
    """
    if stock_name is None:
        stock_name = stock_code
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), 'data')

    print("开始下载股票数据（Tushare 复权日线）")
    print(f"股票：{stock_name}({stock_code})  复权：{adj or '不复权'}")
    print(f"日期范围：{start_date} 至 {end_date}")
    print("-" * 60)

    try:
        print("步骤1：初始化 Tushare Pro...")
        try:
            get_pro()  # 确保 token 已设置，供 ts.pro_bar 使用
        except RuntimeError as e:
            print(f"错误：{e}")
            return None
        print("初始化成功")

        print("\n步骤2：下载日线数据（前复权）...")
        df = ts.pro_bar(
            ts_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            adj=adj,
            freq='D',
        )

        if df is None or len(df) == 0:
            print("错误：无法获取日线数据，请检查 Token 权限或股票代码")
            return None

        df = df.rename(columns={'trade_date': 'date', 'vol': 'volume'})
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date').reset_index(drop=True)
        keep_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        df = df[[c for c in keep_cols if c in df.columns]]

        print(f"成功获取 {len(df)} 条日线数据")
        print(f"数据日期范围：{df['date'].iloc[0].strftime('%Y-%m-%d')} 至 {df['date'].iloc[-1].strftime('%Y-%m-%d')}")

        print("\n步骤3：保存到 CSV...")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'{stock_code.replace(".", "_")}_daily_adj_tushare.csv')
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"数据已保存至：{output_file}")

        print("\n数据预览（前5行）：")
        print(df.head().to_string(index=False))
        print("\n数据统计：")
        print(f"  总记录数：{len(df)}  收盘价范围：{df['close'].min():.2f} - {df['close'].max():.2f}")
        return output_file

    except Exception as e:
        print(f"下载数据过程中发生错误：{e}")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tushare 日线下载（复权），与历史日线脚本并存')
    parser.add_argument('--stock-code', type=str, required=True, help='股票代码，如 600519.SH')
    parser.add_argument('--stock-name', type=str, default=None)
    parser.add_argument('--start-date', type=str, default='20240101', help='开始日期 YYYYMMDD')
    parser.add_argument('--end-date', type=str, default=None, help='结束日期 YYYYMMDD，默认为今天')
    parser.add_argument('--output-dir', type=str, default=None)
    parser.add_argument('--adj', type=str, default='qfq', help='qfq=前复权, hfq=后复权')
    args = parser.parse_args()

    result = download_stock_data(
        stock_code=args.stock_code,
        stock_name=args.stock_name,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
        adj=args.adj,
    )
    if result:
        print("\n" + "=" * 60 + "\n复权日线下载完成! 文件：" + result + "\n" + "=" * 60)
    else:
        print("\n下载失败，请检查错误信息。")
