# -*- coding: utf-8 -*-
"""
多因子选股 - 筛选1（绝对阈值）
5 层漏斗：ROE≥、净利润同比≥、毛利率≥、资产负债率≤、经营现金流/营收≥。
输入为财务池 CSV，输出达标股票 CSV。阈值通过命令行或参数传入。
"""
import os
import sys
import argparse
import pandas as pd

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def run_screen(
    input_file=None,
    output_file=None,
    data_dir=None,
    roe_min=15,
    netprofit_yoy_min=10,
    grossprofit_margin_min=30,
    debt_to_assets_max=60,
    ocf_to_revenue_min=10,
):
    if data_dir is not None and input_file is None:
        input_file = os.path.join(data_dir, 'stock_fina_pool_QMT.csv')
    if data_dir is not None and output_file is None:
        output_file = os.path.join(data_dir, 'stock_fina_selected_QMT.csv')
    if input_file is None:
        input_file = os.path.join(os.getcwd(), 'data', 'stock_fina_pool_QMT.csv')
    if output_file is None:
        output_file = os.path.join(os.path.dirname(input_file), 'stock_fina_selected_QMT.csv')

    print("多因子选股 - 筛选1（绝对阈值）")
    print(f"ROE >= {roe_min}%  |  净利润同比 >= {netprofit_yoy_min}%  |  毛利率 >= {grossprofit_margin_min}%")
    print(f"资产负债率 <= {debt_to_assets_max}%  |  经营现金流/营收 >= {ocf_to_revenue_min}%")
    print("-" * 60)

    if not os.path.exists(input_file):
        print(f"错误：未找到输入文件 {input_file}")
        print("请先运行 download_fina_pool_qmt.py 生成财务池")
        return None

    df = pd.read_csv(input_file, encoding='utf-8-sig')
    print(f"读取 {len(df)} 只股票")

    for col in ['roe', 'netprofit_yoy', 'grossprofit_margin', 'debt_to_assets', 'ocf_to_revenue']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    mask = pd.Series(True, index=df.index)
    if 'roe' in df.columns:
        mask &= (df['roe'] >= roe_min)
        print(f"  第1层 ROE >= {roe_min}%: 剩余 {mask.sum()} 只")
    if 'netprofit_yoy' in df.columns:
        mask &= (df['netprofit_yoy'] >= netprofit_yoy_min)
        print(f"  第2层 净利润同比 >= {netprofit_yoy_min}%: 剩余 {mask.sum()} 只")
    if 'grossprofit_margin' in df.columns:
        mask &= (df['grossprofit_margin'] >= grossprofit_margin_min)
        print(f"  第3层 毛利率 >= {grossprofit_margin_min}%: 剩余 {mask.sum()} 只")
    if 'debt_to_assets' in df.columns:
        mask &= (df['debt_to_assets'] <= debt_to_assets_max)
        print(f"  第4层 资产负债率 <= {debt_to_assets_max}%: 剩余 {mask.sum()} 只")
    if 'ocf_to_revenue' in df.columns:
        mask &= (df['ocf_to_revenue'] >= ocf_to_revenue_min)
        print(f"  第5层 经营现金流/营收 >= {ocf_to_revenue_min}%: 剩余 {mask.sum()} 只")

    selected = df[mask].copy()
    if 'roe' in selected.columns:
        selected = selected.sort_values('roe', ascending=False).reset_index(drop=True)

    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    selected.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n筛选完成：共 {len(selected)} 只股票达标")
    print(f"已保存：{output_file}")

    if len(selected) > 0:
        print("\n" + "=" * 60)
        print("达标股票（按 ROE 排序，前 20）：")
        print("=" * 60)
        disp_cols = ['stock_code', 'stock_name', 'end_date', 'roe', 'netprofit_yoy', 'grossprofit_margin', 'debt_to_assets', 'ocf_to_revenue']
        disp_cols = [c for c in disp_cols if c in selected.columns]
        print(selected[disp_cols].head(20).to_string(index=False))

    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='多因子选股 - 绝对阈值筛选')
    parser.add_argument('--input-file', type=str, default=None, help='财务池 CSV 路径')
    parser.add_argument('--output-file', type=str, default=None, help='输出 CSV 路径')
    parser.add_argument('--data-dir', type=str, default=None, help='数据目录（与 input/output 二选一，默认 data）')
    parser.add_argument('--roe-min', type=float, default=15)
    parser.add_argument('--netprofit-yoy-min', type=float, default=10)
    parser.add_argument('--grossprofit-margin-min', type=float, default=30)
    parser.add_argument('--debt-to-assets-max', type=float, default=60)
    parser.add_argument('--ocf-to-revenue-min', type=float, default=10)
    args = parser.parse_args()

    run_screen(
        input_file=args.input_file,
        output_file=args.output_file,
        data_dir=args.data_dir,
        roe_min=args.roe_min,
        netprofit_yoy_min=args.netprofit_yoy_min,
        grossprofit_margin_min=args.grossprofit_margin_min,
        debt_to_assets_max=args.debt_to_assets_max,
        ocf_to_revenue_min=args.ocf_to_revenue_min,
    )
