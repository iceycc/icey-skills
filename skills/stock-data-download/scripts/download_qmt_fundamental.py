# -*- coding: utf-8 -*-
"""
QMT 财务数据下载（通用脚本）
股票代码、时间区间、输出目录等通过命令行或函数参数传入。
依赖：QMT + xtquant，需先启动 miniQMT 客户端。
"""
import os
import time
import traceback
import argparse
from datetime import datetime
import pandas as pd
from xtquant import xtdata

TABLE_LIST = ['Balance', 'Income', 'CashFlow', 'PershareIndex', 'Capital']


def normalize_timetag(ts_val):
    if ts_val is None:
        return None
    s = str(ts_val).strip()
    if len(s) == 8 and s.isdigit():
        return s
    try:
        v = float(s)
        if v == 0:
            return None
        if v > 1e12:
            v = v / 1000
        return datetime.fromtimestamp(v).strftime('%Y%m%d')
    except (OSError, ValueError, TypeError):
        return None


def get_field(record, field_names, default=None):
    for name in field_names:
        val = record.get(name)
        if val is not None:
            return val
    return default


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


def build_period_map(data_list):
    period_map = {}
    if isinstance(data_list, pd.DataFrame):
        for _, row in data_list.iterrows():
            period_date = normalize_timetag(row.get('m_timetag'))
            if period_date:
                period_map[period_date] = row.to_dict()
    elif isinstance(data_list, list):
        for rec in data_list:
            if isinstance(rec, dict):
                period_date = normalize_timetag(rec.get('m_timetag'))
                if period_date:
                    period_map[period_date] = rec
    return period_map


def extract_all_periods(data, stock_code):
    """从 xtquant 返回的财务数据中提取该股票所有报告期的综合指标。"""
    stock_data = data.get(stock_code, {})
    if not stock_data:
        return []

    pershare_map = build_period_map(stock_data.get('PershareIndex', []))
    balance_map = build_period_map(stock_data.get('Balance', []))
    income_map = build_period_map(stock_data.get('Income', []))
    cashflow_map = build_period_map(stock_data.get('CashFlow', []))
    capital_map = build_period_map(stock_data.get('Capital', []))

    all_periods = sorted(set(
        list(pershare_map.keys()) + list(balance_map.keys()) +
        list(income_map.keys()) + list(cashflow_map.keys())
    ))
    records = []
    for period in all_periods:
        ps = pershare_map.get(period, {})
        bal = balance_map.get(period, {})
        inc = income_map.get(period, {})
        cf = cashflow_map.get(period, {})
        cap = capital_map.get(period, {})

        eps = get_field(ps, ['s_fa_eps_basic'])
        bps = get_field(ps, ['s_fa_bps'])
        ocfps = get_field(ps, ['s_fa_ocfps'])
        undist_ps = get_field(ps, ['s_fa_undistributedps'])
        roe = get_field(ps, ['du_return_on_equity', 'equity_roe', 'net_roe'])
        grossprofit_margin_ps = get_field(ps, ['sales_gross_profit'])

        revenue = get_field(inc, ['revenue', 'operating_revenue', 'revenue_inc'])
        net_profit = get_field(inc, ['net_profit_incl_min_int_inc', 'net_profit_excl_min_int_inc'])
        operating_profit = get_field(inc, ['oper_profit'])
        operating_cost = get_field(inc, ['cost_of_goods_sold', 'total_operating_cost', 'total_expense'])

        grossprofit_margin = grossprofit_margin_ps
        if grossprofit_margin is None and revenue and operating_cost:
            r, c = float(revenue), float(operating_cost)
            if r > 0:
                grossprofit_margin = round((r - c) / r * 100, 2)
        netprofit_margin = safe_divide(net_profit, revenue, pct=True)
        op_margin = safe_divide(operating_profit, revenue, pct=True)

        total_assets = get_field(bal, ['tot_assets'])
        total_liab = get_field(bal, ['tot_liab'])
        total_equity = get_field(bal, ['total_equity', 'tot_shrhldr_eqy_incl_min_int'])
        current_assets = get_field(bal, ['total_current_assets'])
        current_liab = get_field(bal, ['total_current_liability'])
        inventory = get_field(bal, ['inventories'])
        monetary_funds = get_field(bal, ['cash_equivalents'])

        debt_to_assets = safe_divide(total_liab, total_assets, pct=True)
        current_ratio = safe_divide(current_assets, current_liab)
        quick_ratio = safe_divide(
            float(current_assets) - float(inventory), current_liab
        ) if (current_assets and inventory and current_liab) else None

        roa = safe_divide(net_profit, total_assets, pct=True)
        if roe is None and net_profit and total_equity:
            roe = safe_divide(net_profit, total_equity, pct=True)

        assets_turn = safe_divide(revenue, total_assets)
        operating_cashflow = get_field(cf, ['net_cash_flows_oper_act'])
        investing_cashflow = get_field(cf, ['net_cash_flows_inv_act'])
        financing_cashflow = get_field(cf, ['net_cash_flows_fnc_act'])
        ocf_to_revenue = safe_divide(operating_cashflow, revenue, pct=True)
        ocf_to_profit = safe_divide(operating_cashflow, net_profit)
        total_shares = get_field(cap, ['totalShares', 'totalCapital', 'total_shares'])

        record = {
            'end_date': period,
            'eps': eps, 'bps': bps, 'ocfps': ocfps, 'undist_profit_ps': undist_ps,
            'roe': roe, 'roa': roa, 'grossprofit_margin': grossprofit_margin,
            'netprofit_margin': netprofit_margin, 'op_margin': op_margin,
            'debt_to_assets': debt_to_assets, 'current_ratio': current_ratio, 'quick_ratio': quick_ratio,
            'assets_turn': assets_turn,
            'operating_cashflow': operating_cashflow, 'investing_cashflow': investing_cashflow,
            'financing_cashflow': financing_cashflow, 'ocf_to_revenue': ocf_to_revenue, 'ocf_to_profit': ocf_to_profit,
            'total_assets': total_assets, 'total_liab': total_liab, 'total_equity': total_equity,
            'revenue': revenue, 'net_profit': net_profit, 'monetary_funds': monetary_funds, 'total_shares': total_shares,
        }
        records.append(record)
    return records


def download_financial_data(
    stock_code,
    stock_name=None,
    start_date='20150101',
    end_date='20261231',
    output_dir=None,
):
    """
    下载单只股票 QMT 财务数据并保存为 CSV。
    参数：stock_code(如 600519.SH), stock_name, start_date, end_date(YYYYMMDD), output_dir。
    返回：输出文件路径，失败返回 None。
    """
    if stock_name is None:
        stock_name = stock_code
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), 'data')

    print(f"开始下载财务数据（QMT）")
    print(f"股票：{stock_name}({stock_code})  日期：{start_date} 至 {end_date}")
    print("-" * 60)

    try:
        print("步骤0：连接 QMT 数据服务...")
        xtdata.connect()

        print("\n步骤1：下载财务数据到本地缓存...")
        done_count = [0]
        total_tables = len(TABLE_LIST)

        def on_done(_data):
            done_count[0] += 1
            print(f"  已下载 {done_count[0]}/{total_tables} 张报表", flush=True)

        for table_name in TABLE_LIST:
            xtdata.download_financial_data2(
                stock_list=[stock_code],
                table_list=[table_name],
                start_time=start_date,
                end_time=end_date,
                callback=on_done,
            )
        for _ in range(60):
            if done_count[0] >= len(TABLE_LIST):
                break
            time.sleep(1)
        time.sleep(1)

        print("\n步骤2：获取并解析财务数据...")
        data = xtdata.get_financial_data(
            stock_list=[stock_code],
            table_list=TABLE_LIST,
            start_time=start_date,
            end_time=end_date,
            report_type='report_time',
        )
        if not data or stock_code not in data:
            print("错误：无法获取财务数据")
            return None

        records = extract_all_periods(data, stock_code)
        if not records:
            print("错误：未提取到任何财务指标")
            return None

        df = pd.DataFrame(records).sort_values('end_date').reset_index(drop=True)
        print(f"成功提取 {len(df)} 期财务数据")

        print("\n步骤3：保存到 CSV...")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f'{stock_code.replace(".", "_")}_fina_QMT.csv')
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"数据已保存至：{output_file}")
        return output_file

    except Exception as e:
        print(f"下载数据过程中发生错误：{e}")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='QMT 财务数据下载（参数由命令行传入）')
    parser.add_argument('--stock-code', type=str, required=True, help='股票代码，如 600519.SH')
    parser.add_argument('--stock-name', type=str, default=None)
    parser.add_argument('--start-date', type=str, default='20150101', help='开始日期 YYYYMMDD')
    parser.add_argument('--end-date', type=str, default='20261231', help='结束日期 YYYYMMDD')
    parser.add_argument('--output-dir', type=str, default=None)
    args = parser.parse_args()

    result = download_financial_data(
        stock_code=args.stock_code,
        stock_name=args.stock_name,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
    )
    if result:
        print("\n" + "=" * 60 + "\n财务数据下载完成! 文件：" + result + "\n" + "=" * 60)
    else:
        print("\n财务数据下载失败。")
