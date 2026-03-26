"""
数据库配置模块 - 安全读取数据库连接信息
所有敏感信息从环境变量读取
"""
import os

# 数据库配置（从环境变量读取）
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '172.20.0.235'),
    'port': int(os.environ.get('DB_PORT', '13306')),
    'user': os.environ.get('DB_USER', 'e_ds'),
    'password': os.environ.get('DB_PASSWORD', ''),  # 必须从环境变量设置
    'database': os.environ.get('DB_NAME', 'wattrel'),
    'charset': 'utf8mb4'
}

# OpenClaw Webhook配置
OPENCLAW_CONFIG = {
    'webhook': os.environ.get('OPENCLAW_WEBHOOK', 'http://127.0.0.1:18789/hooks/wattrel/wake'),
    'token': os.environ.get('OPENCLAW_HOOK_TOKEN', 'wattrel-webhook-secret-token-2026')
}


def check_db_config():
    """检查数据库配置是否完整"""
    if not DB_CONFIG['password']:
        raise ValueError(
            "DB_PASSWORD环境变量未设置！\n"
            "请执行: export DB_PASSWORD='your_db_password'\n"
            "或在 ~/.bashrc 中添加: export DB_PASSWORD='your_db_password'"
        )
    return True


def get_db_config():
    """获取数据库配置（检查是否设置）"""
    check_db_config()
    return DB_CONFIG


def get_db_connection():
    """获取数据库连接"""
    import pymysql
    check_db_config()
    return pymysql.connect(**DB_CONFIG)
