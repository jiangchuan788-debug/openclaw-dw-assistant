#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精简版告警统计脚本
- 只统计最近两天的告警
- 只关注：数据量不一致、表记录数不一致
- 过滤掉"已恢复"的告警
- 输出简洁报告

作者：OpenClaw
日期：2026-03-23
"""

import urllib.request
import json
import sys
from datetime import datetime, timedelta

# DolphinScheduler 告警数据库配置
DB_CONFIG = {
    'host': '172.20.0.235',
    'port': 13306,
    'user': 'e_ds',
    'password': 'hAN0Hax1lop',
    'database': 'wattrel'
}

# OpenClaw Webhook 配置
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
    """
    查询最近两天的告警
    只查询：数据量不一致、表记录数不一致
    过滤：已恢复的告警
    """
    # 计算两天前的时间
    two_days_ago = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
    
    # 使用 Node.js 查询（因为容器内有 Node 但没有 Python MySQL 库）
    import subprocess
    
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
        SELECT id, content, type, status, created_at
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


def classify_alert(content):
    """
    分类告警类型
    
    Returns:
        tuple: (alert_type, table_name, detail)
    """
    content_lower = content.lower()
    
    # 判断类型
    if '数量不一致' in content or 'count' in content_lower or 'cnt' in content_lower:
        alert_type = '表记录数不一致'
    elif '不一致' in content:
        alert_type = '数据量不一致'
    else:
        alert_type = '其他不一致'
    
    # 提取表名（在"不一致"之前的表名）
    table_name = '未知表'
    
    # 尝试匹配 "表名 不一致" 或 "表名 xxx 不一致"
    import re
    patterns = [
        r'(\w+)\s+.*不一致',
        r'(ods_\w+|dwd_\w+|dws_\w+|ads_\w+|dwb_\w+)',
        r'(biz_\w+|dim_\w+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            table_name = match.group(1)
            break
    
    # 提取期望值/实际值（如果有）
    detail = ''
    if '期望值' in content and '实际值' in content:
        import re
        match = re.search(r'期望值\s*(\d+)\s*实际值\s*(\d+)', content)
        if match:
            expected = match.group(1)
            actual = match.group(2)
            diff = int(actual) - int(expected)
            detail = f'期望: {expected}, 实际: {actual}, 差值: {diff:+d}'
    
    return alert_type, table_name, detail


def format_alert_message(alerts):
    """格式化告警消息"""
    if not alerts:
        return None
    
    # 按类型分组统计
    count_alerts = []  # 记录数不一致
    data_alerts = []   # 数据量不一致
    
    for alert in alerts:
        content = alert.get('content', '')
        alert_type, table_name, detail = classify_alert(content)
        
        alert_info = {
            'id': alert.get('id'),
            'type': alert_type,
            'table': table_name,
            'detail': detail,
            'created_at': alert.get('created_at'),
            'content': content[:100] + '...' if len(content) > 100 else content
        }
        
        if '记录数' in alert_type or '数量' in alert_type:
            count_alerts.append(alert_info)
        else:
            data_alerts.append(alert_info)
    
    # 构建消息
    lines = [
        '🚨 数据质量告警报告（最近两天）',
        '',
        f'📊 总计: {len(alerts)} 条未处理告警',
        f'   • 表记录数不一致: {len(count_alerts)} 条',
        f'   • 数据量不一致: {len(data_alerts)} 条',
        ''
    ]
    
    # 表记录数不一致
    if count_alerts:
        lines.append('📋 表记录数不一致告警:')
        for i, alert in enumerate(count_alerts[:10], 1):  # 最多显示10条
            lines.append(f'{i}. {alert["table"]}')
            if alert['detail']:
                lines.append(f'   {alert["detail"]}')
            lines.append(f'   ⏰ {alert["created_at"]}')
            lines.append('')
        
        if len(count_alerts) > 10:
            lines.append(f'   ... 还有 {len(count_alerts) - 10} 条')
            lines.append('')
    
    # 数据量不一致
    if data_alerts:
        lines.append('📋 数据量不一致告警:')
        for i, alert in enumerate(data_alerts[:10], 1):
            lines.append(f'{i}. {alert["table"]} - {alert["type"]}')
            if alert['detail']:
                lines.append(f'   {alert["detail"]}')
            lines.append(f'   ⏰ {alert["created_at"]}')
            lines.append('')
        
        if len(data_alerts) > 10:
            lines.append(f'   ... 还有 {len(data_alerts) - 10} 条')
            lines.append('')
    
    lines.append('---')
    lines.append('💡 请检查上述表的数据同步状态')
    
    return '\n'.join(lines)


def main():
    """主函数"""
    print('=' * 70)
    print('🚨 精简版告警统计（最近两天）')
    print('=' * 70)
    print()
    
    # 查询告警
    print('🔍 查询最近两天的数据不一致告警...')
    alerts = query_recent_alerts()
    
    print(f'✅ 查询完成，找到 {len(alerts)} 条告警\n')
    
    if not alerts:
        message = '🎉 最近两天没有数据不一致告警！\n\n所有数据质量检查正常。'
        print(message)
        send_alert(message)
        return
    
    # 格式化消息
    message = format_alert_message(alerts)
    
    # 输出到控制台
    print(message)
    print()
    
    # 发送到钉钉
    print('📤 正在发送告警到钉钉群...')
    if send_alert(message):
        print('✅ 发送成功！')
    else:
        print('❌ 发送失败')
    
    print('=' * 70)


if __name__ == '__main__':
    main()
