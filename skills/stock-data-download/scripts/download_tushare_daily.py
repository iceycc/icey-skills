# -*- coding: utf-8 -*-
"""
Tushare数据下载脚本
使用tushare下载股票历史数据
保存到本地CSV文件，供后续策略分析使用

注意：运行此脚本需要安装tushare并配置好TUSHARE_TOKEN环境变量
"""
import os
import pandas as pd
from tushare_pro import get_pro
from datetime import datetime
import argparse


def is_hk_stock(stock_code):
    """
    判断是否为港股
    
    参数:
        stock_code: 股票代码，如 '00700.HK' 或 '600519.SH'
    
    返回:
        True 如果是港股，False 否则
    """
    return stock_code.upper().endswith('.HK')


def download_stock_data(stock_code, stock_name=None, data_start='20150101', data_end=None, output_dir=None):
    """
    下载股票历史数据并保存到CSV文件
    
    参数:
        stock_code: 股票代码，如 '600519.SH' 或 '00700.HK'
        stock_name: 股票名称，可选
        data_start: 数据开始日期，格式 'YYYYMMDD'
        data_end: 数据结束日期，格式 'YYYYMMDD'，默认为今天
        output_dir: 输出目录，默认为当前目录下的 data 文件夹
    
    返回:
        输出文件路径，失败返回 None
    """
    if stock_name is None:
        stock_name = stock_code
    
    if data_end is None:
        data_end = datetime.now().strftime('%Y%m%d')
    
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), 'data')
    
    print(f"开始下载股票数据")
    print(f"股票：{stock_name}({stock_code})")
    print(f"日期范围：{data_start} 至 {data_end}")
    print("-" * 60)
    
    try:
        # 步骤1：初始化tushare
        print("步骤1：初始化tushare...")
        token = os.getenv('TUSHARE_TOKEN')
        if not token:
            print("错误：未找到环境变量 TUSHARE_TOKEN")
            print("请设置环境变量：set TUSHARE_TOKEN=your_token")
            return None
        
        pro = get_pro()
        print("tushare初始化成功")
        
        # 步骤2：下载历史数据
        print("\n步骤2：下载历史数据...")
        # tushare的daily接口需要股票代码格式为：688256.SH
        # 港股使用hk_daily接口，代码格式为：00700.HK
        # 日期格式：YYYYMMDD
        
        # 判断是否为港股，选择对应的接口
        if is_hk_stock(stock_code):
            print(f"检测到港股代码，使用 hk_daily 接口...")
            df = pro.hk_daily(
                ts_code=stock_code,
                start_date=data_start,
                end_date=data_end
            )
        else:
            print(f"检测到A股代码，使用 daily 接口...")
            df = pro.daily(
                ts_code=stock_code,
                start_date=data_start,
                end_date=data_end
            )
        
        if df is None or df.empty:
            print("错误：无法获取历史数据")
            return None
        
        # 步骤3：数据预处理
        print(f"成功获取 {len(df)} 条历史数据")
        
        # 重命名列名，使其与原有格式一致
        df = df.rename(columns={
            'trade_date': 'date',
            'close': 'close',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'vol': 'volume'
        })
        
        # 选择需要的列
        columns_needed = ['date', 'close']
        if 'open' in df.columns:
            columns_needed.append('open')
        if 'high' in df.columns:
            columns_needed.append('high')
        if 'low' in df.columns:
            columns_needed.append('low')
        if 'volume' in df.columns:
            columns_needed.append('volume')
        
        df = df[columns_needed].copy()
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
        
        # 过滤掉无效数据
        df = df.dropna(subset=['date', 'close'])
        df = df.sort_values('date').reset_index(drop=True)
        
        print(f"数据日期范围：{df['date'].iloc[0].strftime('%Y-%m-%d')} 至 {df['date'].iloc[-1].strftime('%Y-%m-%d')}")
        
        # 步骤4：保存到CSV文件
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
    parser = argparse.ArgumentParser(description='Tushare股票数据下载工具')
    parser.add_argument('--stock-code', type=str, required=True, help='股票代码，A股如 600519.SH，港股如 00700.HK')
    parser.add_argument('--stock-name', type=str, default=None, help='股票名称，可选')
    parser.add_argument('--start-date', type=str, default='20150101', help='开始日期，格式 YYYYMMDD')
    parser.add_argument('--end-date', type=str, default=None, help='结束日期，格式 YYYYMMDD，默认为今天')
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
