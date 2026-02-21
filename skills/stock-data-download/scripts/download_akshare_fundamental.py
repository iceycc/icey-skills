# -*- coding: utf-8 -*-
"""
AkShare 单只股票财务数据下载（通用脚本）
股票代码、输出目录等通过命令行或函数参数传入。数据来源：新浪财经三大报表。
依赖：pip install akshare，无需 Token。
"""
import os
import traceback
import argparse
import pandas as pd
import akshare as ak


def _to_sina_code(stock_code):
    """600519.SH -> sh600519, 000001.SZ -> sz000001, 600519 -> sh600519"""
    code = str(stock_code).strip().upper().replace('.', '_')
    if '_' in code:
        num, ex = code.split('_', 1)
        prefix = 'sh' if ex == 'SH' else 'sz'
        return prefix + num
    return 'sh' + code


def _to_file_suffix(stock_code):
    """600519.SH -> 600519_SH"""
    return str(stock_code).strip().upper().replace('.', '_')


def safe_float(val):
    try:
        if val is None or str(val).strip() in ('', '--', 'None', 'nan'):
            return None
        return float(val)
    except (ValueError, TypeError):
        return None


def safe_divide(a, b, pct=False):
    if a is None or b is None:
        return None
    a, b = float(a), float(b)
    if b == 0:
        return None
    result = a / b
    if pct:
        result *= 100
    return round(result, 4)


def get_col(row, col_names, default=None):
    for name in col_names:
        if name in row.index:
            val = safe_float(row[name])
            if val is not None:
                return val
        for col in row.index:
            if name in str(col):
                val = safe_float(row[col])
                if val is not None:
                    return val
    return default


def download_financial_data(
    stock_code,
    stock_name=None,
    output_dir=None,
):
    """
    下载单只股票 AkShare 财务数据（新浪三大报表提取指标）并保存为 CSV。
    参数：stock_code(如 600519.SH 或 600519), stock_name, output_dir。
    返回：输出文件路径，失败返回 None。
    """
    sina_code = _to_sina_code(stock_code)
    file_suffix = _to_file_suffix(stock_code)
    if stock_name is None:
        stock_name = stock_code
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), 'data')

    print(f"开始下载财务数据（AkShare/新浪）")
    print(f"股票：{stock_name}({stock_code}) 新浪代码：{sina_code}")
    print("-" * 60)

    try:
        print("步骤1：下载利润表...")
        df_income = ak.stock_financial_report_sina(stock=sina_code, symbol="利润表")
        print("步骤2：下载资产负债表...")
        df_balance = ak.stock_financial_report_sina(stock=sina_code, symbol="资产负债表")
        print("步骤3：下载现金流量表...")
        df_cashflow = ak.stock_financial_report_sina(stock=sina_code, symbol="现金流量表")

        def normalize_date_col(df):
            date_col_name = df.columns[0]
            df = df.copy()
            df['_date'] = df[date_col_name].astype(str).str.replace('-', '').str[:8]
            return df

        df_income = normalize_date_col(df_income)
        df_balance = normalize_date_col(df_balance)
        df_cashflow = normalize_date_col(df_cashflow)

        income_map = {}
        for _, row in df_income.iterrows():
            period = row['_date']
            if period and len(period) == 8 and period.isdigit():
                income_map[period] = row
        balance_map = {}
        for _, row in df_balance.iterrows():
            period = row['_date']
            if period and len(period) == 8 and period.isdigit():
                balance_map[period] = row
        cashflow_map = {}
        for _, row in df_cashflow.iterrows():
            period = row['_date']
            if period and len(period) == 8 and period.isdigit():
                cashflow_map[period] = row

        all_periods = sorted(set(income_map.keys()) & set(balance_map.keys()))
        print(f"  共 {len(all_periods)} 个报告期")

        records = []
        for period in all_periods:
            inc = income_map.get(period)
            bal = balance_map.get(period)
            cf = cashflow_map.get(period)

            revenue = get_col(inc, ['营业收入', '一、营业收入', '一、营业总收入'])
            operating_cost = get_col(inc, ['营业成本', '二、营业总成本', '营业总成本'])
            net_profit = get_col(inc, ['净利润', '五、净利润', '四、净利润'])
            operating_profit = get_col(inc, ['营业利润', '三、营业利润'])
            eps = get_col(inc, ['基本每股收益', '（一）基本每股收益'])

            total_assets = get_col(bal, ['资产总计', '资产合计'])
            total_liab = get_col(bal, ['负债合计', '负债总计'])
            total_equity = get_col(bal, ['所有者权益合计', '所有者权益（或股东权益）合计', '股东权益合计', '归属于母公司股东权益合计'])
            current_assets = get_col(bal, ['流动资产合计'])
            current_liab = get_col(bal, ['流动负债合计'])
            inventory = get_col(bal, ['存货'])
            monetary_funds = get_col(bal, ['货币资金'])

            operating_cashflow = get_col(cf, ['经营活动产生的现金流量净额']) if cf is not None else None
            investing_cashflow = get_col(cf, ['投资活动产生的现金流量净额']) if cf is not None else None
            financing_cashflow = get_col(cf, ['筹资活动产生的现金流量净额']) if cf is not None else None

            grossprofit_margin = None
            if revenue and operating_cost and revenue > 0:
                grossprofit_margin = round((revenue - operating_cost) / revenue * 100, 2)
            netprofit_margin = safe_divide(net_profit, revenue, pct=True)
            op_margin = safe_divide(operating_profit, revenue, pct=True)
            roe = safe_divide(net_profit, total_equity, pct=True)
            roa = safe_divide(net_profit, total_assets, pct=True)
            debt_to_assets = safe_divide(total_liab, total_assets, pct=True)
            current_ratio = safe_divide(current_assets, current_liab)
            quick_ratio = safe_divide(current_assets - inventory, current_liab) if (current_assets and inventory and current_liab) else None
            assets_turn = safe_divide(revenue, total_assets)
            ocf_to_revenue = safe_divide(operating_cashflow, revenue, pct=True)
            ocf_to_profit = safe_divide(operating_cashflow, net_profit)

            record = {
                'end_date': period,
                'eps': eps, 'roe': roe, 'roa': roa, 'grossprofit_margin': grossprofit_margin,
                'netprofit_margin': netprofit_margin, 'op_margin': op_margin,
                'debt_to_assets': debt_to_assets, 'current_ratio': current_ratio, 'quick_ratio': quick_ratio,
                'assets_turn': assets_turn,
                'operating_cashflow': operating_cashflow, 'investing_cashflow': investing_cashflow,
                'financing_cashflow': financing_cashflow, 'ocf_to_revenue': ocf_to_revenue, 'ocf_to_profit': ocf_to_profit,
                'revenue': revenue, 'net_profit': net_profit, 'total_assets': total_assets,
                'total_liab': total_liab, 'total_equity': total_equity, 'monetary_funds': monetary_funds,
            }
            records.append(record)

        if not records:
            print("错误：未提取到任何财务指标")
            return None

        result_df = pd.DataFrame(records).sort_values('end_date').reset_index(drop=True)
        print(f"成功提取 {len(result_df)} 期财务数据")

        print("\n步骤4：保存到 CSV...")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'{file_suffix}_fina_akshare.csv')
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"数据已保存至：{output_file}")
        return output_file

    except Exception as e:
        print(f"下载数据过程中发生错误：{e}")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AkShare 单只股票财务数据下载（参数由命令行传入）')
    parser.add_argument('--stock-code', type=str, required=True, help='股票代码，如 600519.SH 或 600519')
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
