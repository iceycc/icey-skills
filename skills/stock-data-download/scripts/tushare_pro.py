# -*- coding: utf-8 -*-
"""
Tushare Pro 实例统一初始化，供本目录下所有 Tushare 相关脚本调用。
需环境变量：TUSHARE_TOKEN、TUSHARE_HTTP_URL（Tushare API 地址，如 https://api.tushare.pro）。
"""
import os
import tushare as ts

# 可选：自定义 API 地址。仅从环境变量 TUSHARE_HTTP_URL 读取，不设则使用 Tushare 官方地址（不写死默认代理，避免泄露第三方地址）
DEFAULT_HTTP_URL = os.environ.get("TUSHARE_HTTP_URL", "")


def get_pro():
    """获取 Tushare Pro 实例。需环境变量 TUSHARE_TOKEN、TUSHARE_HTTP_URL。"""
    token = os.environ.get("TUSHARE_TOKEN")
    if not token or not str(token).strip():
        raise RuntimeError("未设置环境变量 TUSHARE_TOKEN")
    if not DEFAULT_HTTP_URL or not DEFAULT_HTTP_URL.strip():
        raise RuntimeError(
            "未设置环境变量 TUSHARE_HTTP_URL，请设置 Tushare API 地址后再调用。"
            " 例如: export TUSHARE_HTTP_URL='https://api.tushare.pro'"
        )
    token = str(token).strip()
    ts.set_token(token)
    pro = ts.pro_api()
    pro._DataApi__token = token
    pro._DataApi__http_url = DEFAULT_HTTP_URL.strip()
    return pro
