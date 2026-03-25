#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤2: 解析告警并查找表位置
"""

import json
import re
import subprocess
from datetime import datetime, timedelta

# 告警数据
alerts = [
  {"id": 4479, "content": "dwd_asset_account_recharge 数量不一致  期望值 54693  实际值54690  差值为 3", "dt_from_sql": "2026-03-24"},
  {"id": 4480, "content": "dwd_asset_qsq_erp_withhold 数量不一致  期望值 663575  实际值663527  差值为 48", "dt_from_sql": "2026-03-24"},
  {"id": 4478, "content": "dwd_asset_account_repay 数量不一致  期望值 139750  实际值139744  差值为 6", "dt_from_sql": "2026-03-24"},
  {"id": 4461, "content": "dwd_asset_clean_clearing_trans 数量不一致  期望值 1443659  实际值1443660  差值为 -1", "dt_from_sql": "2026-03-17"},
  {"id": 4455, "content": "dwd_asset_account_repay 数量不一致  期望值 139750  实际值139744  差值为 6", "dt_from_sql": "2026-03-24"},
  {"id": 4437, "content": "dwd_asset_account_repay 数量不一致  期望值 127272  实际值127404  差值为 -132", "dt_from_sql": "2026-03-23"},
  {"id": 4436, "content": "dwd_asset_account_repay 数量不一致  期望值 127272  实际值127404  差值为 -132", "dt_from_sql": "2026-03-23"},
  {"id": 4434, "content": "dwd_asset_account_repay 数量不一致  期望值 127317  实际值127404  差值为 -87", "dt_from_sql": "2026-03-23"},
]

def extract_table(content):
    """从告警内容提取表名"""
    table_match = re.search(r'(dwd_\w+)', content)
    return table_match.group(1) if table_match else None

def dt_in_range(dt_str, max_days=10):
    """检查dt是否在指定范围内"""
    try:
        dt_date = datetime.strptime(dt_str, '%Y-%m-%d')
        today = datetime.now()
        diff_days = (today - dt_date).days
        return 0 <= diff_days <= max_days
    except:
        return False

# 解析所有告警
print("=" * 80)
print("🔍 步骤2: 解析告警并生成修复计划")
print("=" * 80)

# 去重: 使用(table, dt)作为key
unique_repairs = {}
for alert in alerts:
    table = extract_table(alert['content'])
    dt = alert['dt_from_sql']
    if table and dt:
        key = f"{table}_{dt}"
        if key not in unique_repairs:
            in_range = dt_in_range(dt)
            unique_repairs[key] = {
                'table': table,
                'dt': dt,
                'in_range': in_range,
                'diff_days': (datetime.now() - datetime.strptime(dt, '%Y-%m-%d')).days if dt else None
            }

print(f"\n📋 解析完成: {len(alerts)}条告警 → {len(unique_repairs)}个唯一修复任务")
print("\n修复计划表:")
print("-" * 80)
print(f"{'序号':<4} | {'表名':<35} | {'dt':<12} | {'dt差值':<8} | {'状态':<15}")
print("-" * 80)

repair_list = []
for i, (key, info) in enumerate(unique_repairs.items(), 1):
    status = "✅ 可修复" if info['in_range'] else "❌ 跳过(dt>10天)"
    repair_list.append(info)
    print(f"{i:<4} | {info['table']:<35} | {info['dt']:<12} | {info['diff_days']:<8} | {status}")

print("-" * 80)

# 过滤出可修复的任务
valid_repairs = [r for r in repair_list if r['in_range']]
print(f"\n🎯 可执行任务: {len(valid_repairs)}/{len(repair_list)}")

# 保存到文件
output_file = f"/home/node/.openclaw/workspace/auto_repair_records/{datetime.now().strftime('%Y-%m-%d')}_repair_plan.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "total_alerts": len(alerts),
        "unique_repairs": len(unique_repairs),
        "valid_repairs": len(valid_repairs),
        "repair_list": valid_repairs
    }, f, ensure_ascii=False, indent=2)

print(f"\n💾 修复计划已保存: {output_file}")
