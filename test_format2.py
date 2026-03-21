#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='127.0.0.1', 
    port=3333, 
    user='e_ds', 
    password='hAN0Hax1lop', 
    database='wattrel',
    charset='utf8mb4'
)
cursor = conn.cursor(pymysql.cursors.DictCursor)
# 找一条有完整内容的错误告警
cursor.execute('''SELECT id, type, content, created_at FROM wattrel_quality_alert 
                  WHERE content LIKE "%数量不一致%" 
                  LIMIT 1''')
r = cursor.fetchone()

if r:
    print("原始内容:")
    print(r['content'])
    print("\n" + "="*80 + "\n")
    
    # 格式化
    alert_type = r.get('type', 1)
    alert_level = "P" + str(alert_type) if alert_type else "P1"
    
    content = r['content']
    sql_content = ""
    main_content = content
    if "【执行语句】" in content:
        parts = content.split("【执行语句】", 1)
        main_content = parts[0].strip()
        sql_content = parts[1].strip() if len(parts) > 1 else ""
    
    formatted_msg = f"""【任务名称】数据质量校验任务_{r['id']}
【告警时间】{r['created_at'].strftime('%Y-%m-%d %H:%M:%S') if r.get('created_at') else 'N/A'}
【告警级别】{alert_level}
【告警内容】{main_content}
【执行语句】{sql_content}"""
    
    print("格式化后:")
    print(formatted_msg)
else:
    print("No matching alerts found")

conn.close()
