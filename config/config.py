#!/usr/bin/env python3
"""
配置管理模块 - 安全读取DS Token
支持环境变量和配置文件
"""

import os

# Token通过环境变量获取，不在代码中硬编码
DS_CONFIG = {
    'base_url': 'http://172.20.0.235:12345/dolphinscheduler',
    'token': os.environ.get('DS_TOKEN', ''),  # 从环境变量读取，默认为空
    'project_code': '158514956085248'
}

# TV API配置
TV_CONFIG = {
    'api_url': 'https://tv-service-alert.kuainiu.chat/alert/v2/array',
    'bot_id': 'fbbcabb4-d187-4d9e-8e1e-ba7654a24d1c'
}


def get_ds_token():
    """获取DS Token（优先从环境变量）"""
    token = os.environ.get('DS_TOKEN')
    if not token:
        raise ValueError(
            "DS_TOKEN环境变量未设置！\n"
            "请执行: export DS_TOKEN='your_token_here'\n"
            "或在 ~/.bashrc 中添加: export DS_TOKEN='your_token_here'"
        )
    return token


def check_token_set():
    """检查Token是否已设置"""
    return bool(os.environ.get('DS_TOKEN'))
