# -*- coding: utf-8 -*-
"""
多因子选股 - 筛选2（行业打分）
5 项指标按行业内排名换算 1~5 分，总分≥阈值筛选。可选输出行业分布图。
输入为财务池 CSV，输出达标 CSV 与 data/industry_viz/*.png。
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


def add_industry_percentile(df):
    if 'industry' not in df.columns or df['industry'].isna().all() or (df['industry'] == '').all():
        return df
    df = df.copy()
    valid = df['industry'].notna() & (df['industry'] != '')
    if not valid.any():
        return df
    for col, higher_better in [
        ('roe', True), ('netprofit_yoy', True), ('grossprofit_margin', True),
        ('ocf_to_revenue', True), ('debt_to_assets', False),
    ]:
        if col not in df.columns:
            continue
        pct_col = f'{col}_industry_pct'
        if higher_better:
            df.loc[valid, pct_col] = df.loc[valid].groupby('industry')[col].rank(pct=True, method='average')
        else:
            df.loc[valid, pct_col] = 1 - df.loc[valid].groupby('industry')[col].rank(pct=True, method='average')
    return df


def add_industry_score(df):
    pct_cols = ['roe_industry_pct', 'netprofit_yoy_industry_pct', 'grossprofit_margin_industry_pct',
                'debt_to_assets_industry_pct', 'ocf_to_revenue_industry_pct']

    def pct_to_score(x):
        if pd.isna(x):
            return None
        return min(5, max(1, int(x * 5) + 1))

    score_cols = []
    for pct_col in pct_cols:
        if pct_col not in df.columns:
            continue
        score_col = pct_col.replace('_pct', '_score')
        df[score_col] = df[pct_col].apply(pct_to_score)
        score_cols.append(score_col)
    if score_cols:
        df['industry_score'] = df[score_cols].sum(axis=1)
    return df


def industry_distribution_stats(df):
    if 'industry' not in df.columns or df['industry'].isna().all():
        return None
    valid = df['industry'].notna() & (df['industry'] != '')
    if not valid.any():
        return None
    sub = df.loc[valid]
    metrics = ['roe', 'netprofit_yoy', 'grossprofit_margin', 'debt_to_assets', 'ocf_to_revenue']
    metrics = [m for m in metrics if m in sub.columns]
    if not metrics:
        return None
    agg_dict = {m: ['mean', 'median', 'count'] for m in metrics}
    return sub.groupby('industry').agg(agg_dict).round(2)


def save_industry_visualization(df, output_dir):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi']
        plt.rcParams['axes.unicode_minus'] = False
    except ImportError:
        return
    if 'industry' not in df.columns or df['industry'].isna().all():
        return
    valid = df['industry'].notna() & (df['industry'] != '')
    if not valid.any():
        return
    os.makedirs(output_dir, exist_ok=True)
    for col, label in [('roe', 'ROE (%)'), ('grossprofit_margin', '毛利率 (%)'), ('debt_to_assets', '资产负债率 (%)')]:
        if col not in df.columns:
            continue
        sub = df.loc[valid, ['industry', col]].dropna(subset=[col])
        if sub.empty:
            continue
        ind_agg = sub.groupby('industry')[col].agg(['mean', 'median', 'count'])
        ind_agg = ind_agg[ind_agg['count'] >= 3].sort_values('mean', ascending=(col == 'debt_to_assets'))
        if ind_agg.empty:
            continue
        fig, ax = plt.subplots(figsize=(12, max(6, len(ind_agg) * 0.3)))
        ax.barh(range(len(ind_agg)), ind_agg['mean'], label='均值', alpha=0.8)
        ax.set_yticks(range(len(ind_agg)))
        ax.set_yticklabels(ind_agg.index, fontsize=8)
        ax.set_xlabel(label)
        ax.set_title(f'各行业{label}分布（均值）')
        ax.legend()
        plt.tight_layout()
        out_path = os.path.join(output_dir, f'industry_{col}.png')
        plt.savefig(out_path, dpi=100, bbox_inches='tight')
        plt.close()
        print(f"  已保存行业分布图: {out_path}")


def run_screen(
    input_file=None,
    output_file=None,
    data_dir=None,
    score_min=18,
    enable_viz=True,
    viz_output_dir=None,
):
    if data_dir is not None and input_file is None:
        input_file = os.path.join(data_dir, 'stock_fina_pool_QMT.csv')
    if data_dir is not None and output_file is None:
        output_file = os.path.join(data_dir, 'stock_fina_selected_QMT_industry.csv')
    if data_dir is not None and viz_output_dir is None:
        viz_output_dir = os.path.join(data_dir, 'industry_viz')
    if input_file is None:
        input_file = os.path.join(os.getcwd(), 'data', 'stock_fina_pool_QMT.csv')
    if output_file is None:
        output_file = os.path.join(os.path.dirname(input_file), 'stock_fina_selected_QMT_industry.csv')
    if viz_output_dir is None:
        viz_output_dir = os.path.join(os.path.dirname(input_file), 'industry_viz')

    print("多因子选股 - 筛选2（行业打分）")
    print(f"筛选条件：5 项各 1~5 分（按行业内排名），总分 >= {score_min}")
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

    df = add_industry_percentile(df)
    df = add_industry_score(df)

    mask = (df['industry_score'] >= score_min) & df['industry_score'].notna()
    print(f"  打分制：5 项总分 >= {score_min}: 剩余 {mask.sum()} 只")

    selected = df[mask].copy()
    selected = selected.sort_values('industry_score', ascending=False).reset_index(drop=True)

    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    selected.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n筛选完成：共 {len(selected)} 只股票达标")
    print(f"已保存：{output_file}")

    stats = industry_distribution_stats(df)
    if stats is not None:
        print("\n" + "=" * 60)
        print("各行业指标分布（全市场）：")
        print("=" * 60)
        pd.set_option('display.max_columns', 20)
        pd.set_option('display.width', 200)
        print(stats.to_string())

    if enable_viz:
        print("\n生成行业分布可视化...")
        save_industry_visualization(df, viz_output_dir)

    if len(selected) > 0:
        print("\n" + "=" * 60)
        print("达标股票（按总分排序，前 20）：")
        print("=" * 60)
        disp_cols = ['stock_code', 'stock_name', 'industry', 'industry_score', 'end_date', 'roe',
                    'netprofit_yoy', 'grossprofit_margin', 'debt_to_assets', 'ocf_to_revenue']
        score_cols = [c for c in selected.columns if c.endswith('_industry_score') and c != 'industry_score']
        disp_cols = [c for c in disp_cols if c in selected.columns] + score_cols
        print(selected[disp_cols].head(20).to_string(index=False))

    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='多因子选股 - 行业打分筛选')
    parser.add_argument('--input-file', type=str, default=None)
    parser.add_argument('--output-file', type=str, default=None)
    parser.add_argument('--data-dir', type=str, default=None)
    parser.add_argument('--score-min', type=int, default=18, help='总分阈值，5~25')
    parser.add_argument('--viz', action='store_true', default=True, help='生成行业分布图')
    parser.add_argument('--no-viz', action='store_false', dest='viz')
    parser.add_argument('--viz-output-dir', type=str, default=None)
    args = parser.parse_args()

    run_screen(
        input_file=args.input_file,
        output_file=args.output_file,
        data_dir=args.data_dir,
        score_min=args.score_min,
        enable_viz=args.viz,
        viz_output_dir=args.viz_output_dir,
    )
