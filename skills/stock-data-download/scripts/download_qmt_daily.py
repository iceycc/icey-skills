# -*- coding: utf-8 -*-
"""
QMT数据下载脚本
使用xtquant下载股票历史数据
保存到本地CSV文件，供后续策略分析使用

注意：运行此脚本需要安装QMT并配置好xtquant
"""
import os
import pandas as pd
from xtquant import xtdata
import time
import argparse


def download_stock_data(stock_code, stock_name=None, data_start='20240101', data_end='20251231', output_dir=None):
    """
    下载股票历史数据并保存到CSV文件
    
    参数:
        stock_code: 股票代码，如 '600519.SH'
        stock_name: 股票名称，可选
        data_start: 数据开始日期，格式 'YYYYMMDD'
        data_end: 数据结束日期，格式 'YYYYMMDD'
        output_dir: 输出目录，默认为当前目录下的 data 文件夹
    
    返回:
        输出文件路径，失败返回 None
    """
    if stock_name is None:
        stock_name = stock_code
    
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), 'data')
    
    print(f"开始下载股票数据")
    print(f"股票：{stock_name}({stock_code})")
    print(f"日期范围：{data_start} 至 {data_end}")
    print("-" * 60)
    
    try:
        # 步骤1：下载历史数据
        print("步骤1：下载历史数据...")
        try:
            xtdata.download_history_data(
                stock_code=stock_code,
                period='1d',
                start_time=data_start
            )
            print("下载完成，等待数据写入...")
            time.sleep(2)  # 等待数据写入
        except Exception as e:
            print(f"下载数据时出现警告：{e}")
            print("继续尝试获取数据...")
        
        # 步骤2：获取历史数据
        print("\n步骤2：获取历史收盘价数据...")
        res = xtdata.get_market_data(
            stock_list=[stock_code],
            period='1d',
            start_time=data_start,
            end_time='',
            count=-1,
            dividend_type='front',  # 前复权
            fill_data=True
        )
        
        if not res or 'close' not in res or stock_code not in res['close'].index:
            print("错误：无法获取历史数据")
            return None
        
        # 提取各字段数据
        close_df = res['close']
        open_df = res.get('open', None)
        high_df = res.get('high', None)
        low_df = res.get('low', None)
        volume_df = res.get('volume', None)
        
        # 获取日期列表
        dates = close_df.columns.tolist()
        
        # 构建数据DataFrame
        data_dict = {
            'date': dates,
            'close': close_df.loc[stock_code].values
        }
        
        if open_df is not None and stock_code in open_df.index:
            data_dict['open'] = open_df.loc[stock_code].values
        if high_df is not None and stock_code in high_df.index:
            data_dict['high'] = high_df.loc[stock_code].values
        if low_df is not None and stock_code in low_df.index:
            data_dict['low'] = low_df.loc[stock_code].values
        if volume_df is not None and stock_code in volume_df.index:
            data_dict['volume'] = volume_df.loc[stock_code].values
        
        df = pd.DataFrame(data_dict)
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
        
        # 过滤掉无效数据
        df = df.dropna(subset=['date', 'close'])
        df = df.sort_values('date').reset_index(drop=True)
        
        print(f"成功获取 {len(df)} 条历史数据")
        print(f"数据日期范围：{df['date'].iloc[0].strftime('%Y-%m-%d')} 至 {df['date'].iloc[-1].strftime('%Y-%m-%d')}")
        
        # 步骤3：保存到CSV文件
        print("\n步骤3：保存数据到CSV文件...")
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存完整数据
        output_file = os.path.join(output_dir, f'{stock_code.replace(".", "_")}_daily.csv')
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"数据已保存至：{output_file}")
        
        # 显示数据预览
        print("\n数据预览（前5行）：")
        print(df.head().to_string(index=False))
        print("\n数据预览（后5行）：")
        print(df.tail().to_string(index=False))
        
        # 显示数据统计
        print("\n数据统计信息：")
        print(f"  总记录数：{len(df)}")
        print(f"  收盘价范围：{df['close'].min():.2f} - {df['close'].max():.2f}")
        if 'volume' in df.columns:
            print(f"  成交量范围：{df['volume'].min():,.0f} - {df['volume'].max():,.0f}")
        
        return output_file
        
    except Exception as e:
        print(f"下载数据过程中发生错误：{e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='QMT股票数据下载工具')
    parser.add_argument('--stock-code', type=str, required=True, help='股票代码，如 600519.SH')
    parser.add_argument('--stock-name', type=str, default=None, help='股票名称，可选')
    parser.add_argument('--start-date', type=str, default='20240101', help='开始日期，格式 YYYYMMDD')
    parser.add_argument('--end-date', type=str, default='20251231', help='结束日期，格式 YYYYMMDD')
    parser.add_argument('--output-dir', type=str, default=None, help='输出目录，默认为当前目录下的 data 文件夹')
    
    args = parser.parse_args()
    
    result = download_stock_data(
        stock_code=args.stock_code,
        stock_name=args.stock_name,
        data_start=args.start_date,
        data_end=args.end_date,
        output_dir=args.output_dir
    )
    
    if result:
        print("\n" + "=" * 60)
        print("数据下载完成!")
        print(f"数据文件：{result}")
        print("=" * 60)
    else:
        print("\n数据下载失败，请检查错误信息。")
