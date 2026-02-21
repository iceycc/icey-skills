# -*- coding: utf-8 -*-
"""
AkShare 日线数据下载（通用脚本）
股票代码、时间区间、输出目录等通过命令行或函数参数传入，无写死配置。
依赖：pip install akshare
"""
import os
import traceback
import argparse
import pandas as pd
import akshare as ak


def _normalize_stock_code(stock_code):
    """将 600519.SH / 600519 转为 (纯数字代码, 完整代码用于文件名)"""
    code = str(stock_code).strip().upper()
    if '.' in code:
        num, _ = code.split('.', 1)
        full = code.replace('.', '_')
    else:
        num = code
        full = code + '_SH'  # 默认按沪市，仅用于文件名
    return num, full


def download_stock_data(
    stock_code,
    stock_name=None,
    start_date='20240101',
    end_date='20251231',
    output_dir=None,
):
    """
    下载股票日线数据并保存为 CSV。

    参数:
        stock_code: 股票代码，如 '600519' 或 '600519.SH'
        stock_name: 股票名称，可选
        start_date: 开始日期，格式 YYYYMMDD
        end_date: 结束日期，格式 YYYYMMDD
        output_dir: 输出目录，默认当前目录下的 data

    返回:
        输出文件路径，失败返回 None
    """
    code_num, code_full = _normalize_stock_code(stock_code)
    if stock_name is None:
        stock_name = stock_code
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), 'data')

    print(f"开始下载股票数据（AkShare）")
    print(f"股票：{stock_name}({stock_code})")
    print(f"日期范围：{start_date} 至 {end_date}")
    print("-" * 60)

    try:
        print("步骤1：通过 AkShare 下载日线数据（前复权）...")
        df = ak.stock_zh_a_hist(
            symbol=code_num,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )

        if df is None or len(df) == 0:
            print("错误：无法获取日线数据，请检查股票代码")
            return None

        print("步骤2：整理数据格式...")
        col_map = {
            '日期': 'date', '开盘': 'open', '收盘': 'close', '最高': 'high',
            '最低': 'low', '成交量': 'volume',
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        keep_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        df = df[[c for c in keep_cols if c in df.columns]]

        print(f"成功获取 {len(df)} 条日线数据")
        print(f"数据日期范围：{df['date'].iloc[0].strftime('%Y-%m-%d')} 至 {df['date'].iloc[-1].strftime('%Y-%m-%d')}")

        print("\n步骤3：保存到 CSV...")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'{code_full}_daily_akshare.csv')
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
    parser = argparse.ArgumentParser(description='AkShare 日线数据下载（股票代码、时间区间由参数传入）')
    parser.add_argument('--stock-code', type=str, required=True, help='股票代码，如 600519 或 600519.SH')
    parser.add_argument('--stock-name', type=str, default=None, help='股票名称，可选')
    parser.add_argument('--start-date', type=str, default='20240101', help='开始日期 YYYYMMDD')
    parser.add_argument('--end-date', type=str, default='20251231', help='结束日期 YYYYMMDD')
    parser.add_argument('--output-dir', type=str, default=None, help='输出目录，默认 ./data')
    args = parser.parse_args()

    result = download_stock_data(
        stock_code=args.stock_code,
        stock_name=args.stock_name,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
    )
    if result:
        print("\n" + "=" * 60 + "\n数据下载完成! 文件：" + result + "\n" + "=" * 60)
    else:
        print("\n数据下载失败，请检查错误信息。")
