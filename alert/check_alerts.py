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
cursor.execute('SELECT id, type, content, created_at FROM wattrel_quality_alert LIMIT 5')
rows = cursor.fetchall()

for r in rows:
    print(f"ID: {r['id']}, Type: {r['type']}, Created: {r['created_at']}")
    print(f"Content: {r['content'][:300]}...")
    print('-' * 80)

conn.close()
