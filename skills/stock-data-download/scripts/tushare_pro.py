# -*- coding: utf-8 -*-
"""
Tushare Pro 实例统一初始化，供本目录下所有 Tushare 相关脚本调用。
需环境变量 TUSHARE_TOKEN。可选环境变量 TUSHARE_HTTP_URL 指定 API 地址，未设置时使用默认代理。
"""
import os
import tushare as ts

# 可选：自定义 API 地址。仅从环境变量 TUSHARE_HTTP_URL 读取，不设则使用 Tushare 官方地址（不写死默认代理，避免泄露第三方地址）
DEFAULT_HTTP_URL = os.environ.get("TUSHARE_HTTP_URL", "")


def get_pro():
    """获取 Tushare Pro 实例。需环境变量 TUSHARE_TOKEN。"""
    token = os.environ.get("TUSHARE_TOKEN")
    if not token or not str(token).strip():
        raise RuntimeError("未设置环境变量 TUSHARE_TOKEN")
    token = str(token).strip()
    ts.set_token(token)
    pro = ts.pro_api()
    pro._DataApi__token = token
    if DEFAULT_HTTP_URL:
        pro._DataApi__http_url = DEFAULT_HTTP_URL
    return pro
