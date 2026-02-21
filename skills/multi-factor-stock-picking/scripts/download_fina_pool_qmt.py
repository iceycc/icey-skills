# -*- coding: utf-8 -*-
"""
多因子选股 - 财务池下载（QMT）
从 QMT 下载指定板块内所有股票的财务数据，输出带 ROE、净利润同比、名称、行业的 CSV。
板块、日期、输出目录等通过命令行或参数传入。
"""
import os
import sys
import time
import traceback
import argparse
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from xtquant import xtdata

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

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
        revenue = get_field(inc, ['revenue', 'operating_revenue', 'revenue_inc'])
        net_profit = get_field(inc, ['net_profit_incl_min_int_inc', 'net_profit_excl_min_int_inc'])
        operating_profit = get_field(inc, ['oper_profit'])
        operating_cost = get_field(inc, ['cost_of_goods_sold', 'total_operating_cost', 'total_expense'])
        grossprofit_margin = get_field(ps, ['sales_gross_profit'])
        if grossprofit_margin is None and revenue and operating_cost:
            r, c = float(revenue), float(operating_cost)
            if r > 0:
                grossprofit_margin = round((r - c) / r * 100, 2)
        roe = get_field(ps, ['du_return_on_equity', 'equity_roe', 'net_roe'])
        netprofit_margin = safe_divide(net_profit, revenue, pct=True)
        total_assets = get_field(bal, ['tot_assets'])
        total_liab = get_field(bal, ['tot_liab'])
        total_equity = get_field(bal, ['total_equity', 'tot_shrhldr_eqy_incl_min_int'])
        current_assets = get_field(bal, ['total_current_assets'])
        current_liab = get_field(bal, ['total_current_liability'])
        inventory = get_field(bal, ['inventories'])
        debt_to_assets = safe_divide(total_liab, total_assets, pct=True)
        current_ratio = safe_divide(current_assets, current_liab)
        quick_ratio = safe_divide(float(current_assets) - float(inventory), current_liab) if (current_assets and inventory and current_liab) else None
        roa = safe_divide(net_profit, total_assets, pct=True)
        if roe is None and net_profit and total_equity:
            roe = safe_divide(net_profit, total_equity, pct=True)
        assets_turn = safe_divide(revenue, total_assets)
        operating_cashflow = get_field(cf, ['net_cash_flows_oper_act'])
        ocf_to_revenue = safe_divide(operating_cashflow, revenue, pct=True)
        ocf_to_profit = safe_divide(operating_cashflow, net_profit)
        record = {
            'end_date': period,
            'eps': eps, 'bps': bps, 'ocfps': ocfps, 'roe': roe, 'roa': roa,
            'grossprofit_margin': grossprofit_margin, 'netprofit_margin': netprofit_margin,
            'debt_to_assets': debt_to_assets, 'current_ratio': current_ratio, 'quick_ratio': quick_ratio,
            'assets_turn': assets_turn, 'operating_cashflow': operating_cashflow,
            'ocf_to_revenue': ocf_to_revenue, 'ocf_to_profit': ocf_to_profit,
            'revenue': revenue, 'net_profit': net_profit, 'total_assets': total_assets, 'total_equity': total_equity,
        }
        records.append(record)
    return records


def calc_netprofit_yoy(records):
    annual = [r for r in records if str(r.get('end_date', '')).endswith('1231')]
    if len(annual) < 2:
        return None
    annual = sorted(annual, key=lambda x: x['end_date'])
    profits = [float(r['net_profit']) for r in annual if r.get('net_profit') is not None]
    if len(profits) < 2:
        return None
    yoy = pd.Series(profits).pct_change().iloc[-1] * 100
    return round(yoy, 2)


def get_stock_industry_map():
    stock_to_industry = {}
    try:
        all_sectors = xtdata.get_sector_list()
        sw1_sectors = [s for s in all_sectors if str(s).upper().startswith('SW1') and '加权' not in str(s)]
        for sector in sw1_sectors:
            stocks = xtdata.get_stock_list_in_sector(sector)
            if stocks:
                for stk in stocks:
                    if '.' in str(stk):
                        stock_to_industry[stk] = sector
    except Exception as e:
        print(f"获取行业映射异常: {e}")
    return stock_to_industry


def get_stock_name(stock_code):
    try:
        detail = xtdata.get_instrument_detail(stock_code)
        if detail:
            return detail.get('InstrumentName', '') or ''
    except Exception:
        pass
    return ''


def download_one_stock(stock_code, industry_map, data_start, data_end):
    done_count = [0]
    def on_done(_):
        done_count[0] += 1
    for table_name in TABLE_LIST:
        xtdata.download_financial_data2(
            stock_list=[stock_code],
            table_list=[table_name],
            start_time=data_start,
            end_time=data_end,
            callback=on_done,
        )
    for _ in range(60):
        if done_count[0] >= len(TABLE_LIST):
            break
        time.sleep(0.2)
    time.sleep(0.3)
    data = xtdata.get_financial_data(
        stock_list=[stock_code],
        table_list=TABLE_LIST,
        start_time=data_start,
        end_time=data_end,
        report_type='report_time',
    )
    if not data or stock_code not in data:
        return None
    records = extract_all_periods(data, stock_code)
    if not records:
        return None
    records = sorted(records, key=lambda x: x['end_date'])
    latest = records[-1].copy()
    latest['netprofit_yoy'] = calc_netprofit_yoy(records)
    latest['stock_code'] = stock_code
    latest['stock_name'] = get_stock_name(stock_code)
    latest['industry'] = (industry_map or {}).get(stock_code, '')
    return latest


def run_download(
    sector='沪深A股',
    data_start='20150101',
    data_end=None,
    output_dir=None,
    num_workers=8,
    output_filename='stock_fina_pool_QMT.csv',
):
    if data_end is None:
        data_end = date.today().strftime('%Y%m%d')
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), 'data')
    output_file = os.path.join(output_dir, output_filename)

    print("多因子选股 - 财务数据下载（QMT）")
    print(f"板块：{sector}  日期：{data_start} ~ {data_end}")
    print("-" * 50)

    try:
        print("连接 QMT...")
        xtdata.connect()
        print("获取股票列表...")
        stock_list = xtdata.get_stock_list_in_sector(sector)
        if not stock_list:
            sectors = xtdata.get_sector_list()
            print(f"错误：板块 '{sector}' 返回空列表")
            if sectors:
                hs = [s for s in sectors if '沪深' in str(s)][:15]
                print(f"含'沪深'的板块示例：{hs}")
            return None
        stock_list = [c for c in stock_list if '.' in str(c)]
        total = len(stock_list)
        print(f"共 {total} 只股票待下载")
        print("获取行业映射...")
        industry_map = get_stock_industry_map()
        print(f"  已映射 {len(industry_map)} 只股票行业")

        pool = []
        failed = []
        start_time = time.time()

        def _download(code):
            try:
                row = download_one_stock(code, industry_map, data_start, data_end)
                return code, row
            except Exception:
                return code, None

        print(f"并行下载（{num_workers} 线程）...")
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(_download, code): code for code in stock_list}
            done = 0
            for future in as_completed(futures):
                code, row = future.result()
                if row:
                    pool.append(row)
                else:
                    failed.append(code)
                done += 1
                elapsed = time.time() - start_time
                pct = done * 100 / total
                speed = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / speed if speed > 0 else 0
                sys.stdout.write(f"\r获取财务 {done}/{total} ({pct:.1f}%) | {speed:.1f} 只/秒 | 剩余约 {eta:.0f} 秒 | 成功 {len(pool)} 只    ")
                sys.stdout.flush()
        elapsed = time.time() - start_time
        print(f"\n  完成，耗时 {elapsed:.1f} 秒")

        if not pool:
            print("错误：未成功提取任何股票数据")
            return None

        df = pd.DataFrame(pool)
        cols_order = ['stock_code', 'stock_name', 'industry', 'end_date', 'roe', 'netprofit_yoy',
                      'grossprofit_margin', 'debt_to_assets', 'current_ratio', 'operating_cashflow',
                      'ocf_to_revenue', 'ocf_to_profit', 'net_profit', 'revenue', 'eps', 'bps',
                      'roa', 'netprofit_margin', 'quick_ratio', 'assets_turn', 'total_assets', 'total_equity']
        for c in cols_order:
            if c not in df.columns:
                df[c] = None
        df = df[[c for c in cols_order if c in df.columns]]
        os.makedirs(output_dir, exist_ok=True)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n成功 {len(pool)} 只，失败 {len(failed)} 只")
        print(f"已保存：{output_file}")
        if failed:
            print(f"失败列表（前 10 个）：{failed[:10]}")
        return output_file
    except Exception as e:
        print(f"错误：{e}")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='多因子选股 - 财务池下载（QMT）')
    parser.add_argument('--sector', type=str, default='沪深A股', help='板块名称，如 沪深A股')
    parser.add_argument('--start-date', type=str, default='20150101', help='开始日期 YYYYMMDD')
    parser.add_argument('--end-date', type=str, default=None, help='结束日期 YYYYMMDD，默认今天')
    parser.add_argument('--output-dir', type=str, default=None, help='输出目录，默认 ./data')
    parser.add_argument('--num-workers', type=int, default=8, help='并行线程数')
    parser.add_argument('--output-filename', type=str, default='stock_fina_pool_QMT.csv', help='输出文件名')
    args = parser.parse_args()

    result = run_download(
        sector=args.sector,
        data_start=args.start_date,
        data_end=args.end_date,
        output_dir=args.output_dir,
        num_workers=args.num_workers,
        output_filename=args.output_filename,
    )
    if result:
        print("\n下载完成")
    else:
        print("\n下载失败")
