#!/usr/bin/env python3
import pymysql
from datetime import datetime

conn = pymysql.connect(
    host='127.0.0.1', 
    port=3333, 
    user='e_ds', 
    password='hAN0Hax1lop', 
    database='wattrel',
    charset='utf8mb4'
)
cursor = conn.cursor(pymysql.cursors.DictCursor)
cursor.execute('SELECT id, type, content, created_at FROM wattrel_quality_alert WHERE status = 1 ORDER BY id DESC LIMIT 2')
rows = cursor.fetchall()

for alert in rows:
    alert_type = alert.get('type', 1)
    alert_level = "P" + str(alert_type) if alert_type else "P1"
    
    content = alert['content']
    sql_content = ""
    main_content = content
    if "【执行语句】" in content:
        parts = content.split("【执行语句】", 1)
        main_content = parts[0].strip()
        sql_content = parts[1].strip() if len(parts) > 1 else ""
    
    formatted_msg = f"""【任务名称】数据质量校验任务_{alert['id']}
【告警时间】{alert['created_at'].strftime('%Y-%m-%d %H:%M:%S') if alert.get('created_at') else 'N/A'}
【告警级别】{alert_level}
【告警内容】{main_content}
【执行语句】{sql_content}"""
    
    print("=" * 80)
    print(formatted_msg)
    print("=" * 80)
    print()

conn.close()
