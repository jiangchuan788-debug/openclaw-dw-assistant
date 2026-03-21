#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本：查看数据库中的告警内容
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pymysql

DB_HOST = '127.0.0.1'
DB_PORT = 3333
DB_USER = 'e_ds'
DB_PASS = 'hAN0Hax1lop'
DB_NAME = 'wattrel'

conn = pymysql.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASS,
    database=DB_NAME,
    charset='utf8mb4'
)

cursor = conn.cursor(pymysql.cursors.DictCursor)

# 查询最近 2 条未处理告警
cursor.execute("""
    SELECT a.id, a.content, a.created_at, a.type, a.status, r.begin, r.end 
    FROM wattrel_quality_alert a
    LEFT JOIN wattrel_quality_result r ON a.quality_result_id = r.id
    WHERE a.status = 0 
      AND a.created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
    ORDER BY a.created_at ASC
    LIMIT 2
""")

alerts = cursor.fetchall()
conn.close()

print("=" * 80)
print(f"📊 数据库中的告警数据 (共 {len(alerts)} 条)")
print("=" * 80)

for i, alert in enumerate(alerts, 1):
    print(f"\n--- 告警 #{i} ---")
    print(f"ID:         {alert['id']}")
    print(f"类型:       {alert.get('type', 1)}")
    print(f"状态:       {alert.get('status', 0)}")
    print(f"创建时间：  {alert['created_at']}")
    print(f"校验开始：  {alert.get('begin', 'N/A')}")
    print(f"校验结束：  {alert.get('end', 'N/A')}")
    print(f"\n原始内容:")
    print("-" * 80)
    print(alert.get('content', ''))
    print("-" * 80)

print("\n" + "=" * 80)
