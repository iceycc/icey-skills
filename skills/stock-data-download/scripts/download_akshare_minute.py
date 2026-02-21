# -*- coding: utf-8 -*-
"""
AkShare 分钟数据下载（通用脚本）
股票代码、目标日期、周期、输出目录等通过命令行或函数参数传入。
依赖：pip install akshare。仅支持最近 5 个交易日的分钟数据。
"""
import os
import traceback
import argparse
import pandas as pd
import akshare as ak


def _normalize_stock_code(stock_code):
    """600519.SH / 600519 -> (纯数字, 完整用于文件名)"""
    code = str(stock_code).strip().upper()
    if '.' in code:
        num = code.split('.', 1)[0]
        full = code.replace('.', '_')
    else:
        num = code
        full = code + '_SH'
    return num, full


def download_minute_data(
    stock_code,
    stock_name=None,
    target_date='2026-02-10',
    period='1',
    output_dir=None,
):
    """
    下载指定日期的分钟 K 线并保存为 CSV。
    AkShare 仅能获取最近 5 个交易日的分钟数据。

    参数:
        stock_code: 股票代码，如 '600519' 或 '600519.SH'
        stock_name: 股票名称，可选
        target_date: 目标日期，格式 YYYYMMDD 或 YYYY-MM-DD
        period: 分钟周期，'1', '5', '15', '30', '60'
        output_dir: 输出目录，默认当前目录下的 data

    返回:
        输出文件路径，失败返回 None
    """
    code_num, code_full = _normalize_stock_code(stock_code)
    if stock_name is None:
        stock_name = stock_code
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), 'data')

    # 统一成 YYYY-MM-DD 给 akshare
    td = str(target_date).strip().replace('-', '')
    if len(td) == 8:
        start_dt = f"{td[:4]}-{td[4:6]}-{td[6:8]} 09:30:00"
        end_dt = f"{td[:4]}-{td[4:6]}-{td[6:8]} 15:00:00"
    else:
        start_dt = f"{target_date} 09:30:00"
        end_dt = f"{target_date} 15:00:00"

    print(f"开始下载分钟数据（AkShare）")
    print(f"股票：{stock_name}({stock_code})  日期：{target_date}  周期：{period}分钟")
    print("（注意：仅支持最近 5 个交易日）")
    print("-" * 60)

    try:
        print("步骤1：下载分钟数据...")
        df = ak.stock_zh_a_hist_min_em(
            symbol=code_num,
            start_date=start_dt,
            end_date=end_dt,
            period=period,
            adjust='',
        )

        if df is None or len(df) == 0:
            print("错误：无法获取分钟数据（可能超出最近5个交易日或非交易日）")
            return None

        print("步骤2：整理数据格式...")
        col_map = {
            '时间': 'datetime', '开盘': 'open', '收盘': 'close', '最高': 'high',
            '最低': 'low', '成交量': 'volume', '成交额': 'amount',
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        keep_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume', 'amount']
        df = df[[c for c in keep_cols if c in df.columns]]

        print(f"成功获取 {len(df)} 条分钟数据")
        print(f"时间范围：{df['datetime'].iloc[0]} 至 {df['datetime'].iloc[-1]}")

        print("\n步骤3：保存到 CSV...")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'{code_full}_1min_akshare.csv')
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"数据已保存至：{output_file}")
        return output_file

    except Exception as e:
        print(f"下载数据过程中发生错误：{e}")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AkShare 分钟数据下载（参数由命令行传入）')
    parser.add_argument('--stock-code', type=str, required=True, help='股票代码，如 600519 或 600519.SH')
    parser.add_argument('--stock-name', type=str, default=None)
    parser.add_argument('--target-date', type=str, default='2026-02-10', help='目标日期 YYYYMMDD 或 YYYY-MM-DD')
    parser.add_argument('--period', type=str, default='1', help='分钟周期：1, 5, 15, 30, 60')
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
