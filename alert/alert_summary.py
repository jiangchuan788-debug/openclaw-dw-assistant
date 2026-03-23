#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精简版告警脚本 - 保持原有格式
- 只统计最近两天的告警
- 只关注：数据量不一致、表记录数不一致
- 过滤掉"已恢复"的告警
- 原封不动输出告警内容

作者：OpenClaw
日期：2026-03-23
"""

import urllib.request
import json
import sys
import subprocess
from datetime import datetime, timedelta

# 配置
DB_CONFIG = {
    'host': '172.20.0.235',
    'port': 13306,
    'user': 'e_ds',
    'password': 'hAN0Hax1lop',
    'database': 'wattrel'
}

WEBHOOK_URL = 'http://127.0.0.1:18789/hooks/wattrel/wake'
WEBHOOK_TOKEN = 'wattrel-webhook-secret-token-2026'


def send_alert(message):
    """发送告警到钉钉群"""
    try:
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=json.dumps({'text': message, 'mode': 'now'}).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {WEBHOOK_TOKEN}'
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"发送失败: {e}")
        return False


def query_recent_alerts():
    """查询最近两天的数据不一致告警"""
    two_days_ago = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
    
    js_code = f"""
const mysql = require('/tmp/node_modules/mysql2/promise');

async function query() {{
    const conn = await mysql.createConnection({{
        host: '{DB_CONFIG['host']}',
        port: {DB_CONFIG['port']},
        user: '{DB_CONFIG['user']}',
        password: '{DB_CONFIG['password']}',
        database: '{DB_CONFIG['database']}',
        charset: 'utf8mb4'
    }});
    
    const [rows] = await conn.execute(`
        SELECT id, content, type, created_at
        FROM wattrel_quality_alert
        WHERE created_at >= ?
          AND status = 0
          AND content NOT LIKE '%已恢复%'
          AND (
              content LIKE '%数量不一致%'
              OR content LIKE '%不一致%'
          )
        ORDER BY created_at DESC
    `, ['{two_days_ago}']);
    
    await conn.end();
    console.log(JSON.stringify(rows));
}}

query().catch(e => {{ console.error(e); process.exit(1); }});
"""
    
    try:
        result = subprocess.run(
            ['node', '-e', js_code],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"查询失败: {result.stderr}")
            return []
    except Exception as e:
        print(f"执行失败: {e}")
        return []


def format_alert(alert):
    """
    格式化告警消息 - 保持原有格式
    和 alert_bridge_node.js 一致的格式
    """
    alert_id = alert.get('id')
    content = alert.get('content', '')
    created_at = alert.get('created_at')
    alert_type = alert.get('type', '1')
    
    # 解析内容，提取主要部分和SQL
    main_content = content
    sql_content = ''
    
    if '【执行语句】' in content:
        parts = content.split('【执行语句】', 1)
        main_content = parts[0].strip()
        sql_content = parts[1].strip()
    
    # 格式化时间
    try:
        dt = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ')
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        time_str = str(created_at)
    
    # 构建消息 - 保持原有格式
    lines = [
        f"【任务名称】数据质量校验任务_{alert_id}",
        f"【告警时间】{time_str}",
        f"【告警级别】P{alert_type}",
        f"【告警内容】{main_content}",
    ]
    
    if sql_content:
        lines.append(f"【执行语句】{sql_content}")
    
    return '\n'.join(lines)


def main():
    """主函数"""
    print('=' * 70)
    print('🚨 精简版告警报告（最近两天）')
    print('=' * 70)
    print()
    
    # 查询告警
    print('🔍 查询最近两天的数据不一致告警...')
    alerts = query_recent_alerts()
    
    print(f'✅ 找到 {len(alerts)} 条告警\n')
    
    if not alerts:
        message = '🎉 最近两天没有数据不一致告警！\n\n所有数据质量检查正常。'
        print(message)
        send_alert(message)
        return
    
    # 发送报告头部
    header = f"🚨 数据质量告警报告（最近两天）\n\n📊 发现 {len(alerts)} 条未处理的数据不一致告警\n"
    print(header)
    send_alert(header)
    
    # 逐条发送告警（保持原有格式）
    print('=' * 70)
    for i, alert in enumerate(alerts, 1):
        formatted = format_alert(alert)
        
        print(f"\n[{i}/{len(alerts)}]")
        print('-' * 70)
        print(formatted)
        print()
        
        # 发送单条告警
        if send_alert(formatted):
            print(f"✅ 已发送")
        else:
            print(f"❌ 发送失败")
        print()
    
    # 发送结束标记
    footer = f"{'=' * 50}\n💡 以上共 {len(alerts)} 条数据不一致告警，请检查数据同步状态\n{'=' * 50}"
    print(footer)
    send_alert(footer)
    
    print('=' * 70)


if __name__ == '__main__':
    main()
