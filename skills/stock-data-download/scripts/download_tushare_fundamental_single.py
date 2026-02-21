# -*- coding: utf-8 -*-
"""
Tushare 单只股票财务数据下载（通用脚本）
股票代码、输出目录等通过命令行或函数参数传入。
依赖：pip install tushare，环境变量 TUSHARE_TOKEN。需约 2000 积分。
"""
import os
import traceback
import argparse
import pandas as pd

from tushare_pro import get_pro

FINA_FIELDS = ",".join([
    "ts_code", "ann_date", "end_date",
    "eps", "dt_eps", "bps", "ocfps", "undist_profit_ps", "total_revenue_ps",
    "roe", "roe_waa", "roe_dt", "roa", "grossprofit_margin", "netprofit_margin",
    "profit_to_gr", "op_of_gr", "ebit_of_gr",
    "debt_to_assets", "current_ratio", "quick_ratio", "cash_ratio",
    "netprofit_yoy", "dt_netprofit_yoy", "or_yoy", "op_yoy", "ocf_yoy",
    "bps_yoy", "assets_yoy", "eqt_yoy",
    "assets_turn", "inv_turn", "ar_turn", "ca_turn", "fa_turn",
    "invturn_days", "arturn_days",
    "fcff", "fcfe", "salescash_to_or", "ocf_to_or", "ocf_to_opincome",
    "op_income", "ebit", "ebitda",
])


def download_financial_data(
    stock_code,
    stock_name=None,
    output_dir=None,
):
    """
    下载单只股票 Tushare 综合财务指标（所有历史报告期）并保存为 CSV。
    参数：stock_code(如 600519.SH), stock_name, output_dir。
    返回：输出文件路径，失败返回 None。
    """
    if stock_name is None:
        stock_name = stock_code
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), 'data')

    print(f"开始下载财务数据（Tushare）")
    print(f"股票：{stock_name}({stock_code})")
    print("-" * 60)

    try:
        pro = get_pro()
        print("\n步骤1：获取综合财务指标...")
        df = pro.fina_indicator(ts_code=stock_code, fields=FINA_FIELDS)

        if df is None or len(df) == 0:
            print("错误：无法获取财务指标（请检查 Token 权限，需约 2000 积分）")
            return None

        df = df.sort_values('end_date').reset_index(drop=True)
        print(f"成功获取 {len(df)} 期财务数据")
        print(f"报告期范围：{df['end_date'].iloc[0]} 至 {df['end_date'].iloc[-1]}")

        print("\n步骤2：保存到 CSV...")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'{stock_code.replace(".", "_")}_fina_tushare.csv')
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"数据已保存至：{output_file}")

        print("\n数据预览（最近 3 期）：")
        print(df.tail(3).set_index('end_date').T.to_string())
        return output_file

    except Exception as e:
        print(f"下载数据过程中发生错误：{e}")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tushare 单只股票财务数据下载（参数由命令行传入）')
    parser.add_argument('--stock-code', type=str, required=True, help='股票代码，如 600519.SH')
    parser.add_argument('--stock-name', type=str, default=None)
    parser.add_argument('--output-dir', type=str, default=None)
    args = parser.parse_args()

    result = download_financial_data(
        stock_code=args.stock_code,
        stock_name=args.stock_name,
        output_dir=args.output_dir,
    )
    if result:
        print("\n" + "=" * 60 + "\n财务数据下载完成! 文件：" + result + "\n" + "=" * 60)
    else:
        print("\n财务数据下载失败。")
