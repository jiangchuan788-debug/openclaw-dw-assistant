#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用sessions_send直接发送告警到钉钉群
绕过webhook，直接发送到当前活跃会话
"""

import json
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

# 钉钉群会话Key（从sessions.json获取的最新群聊会话）
DINGTALK_SESSION_KEY = 'agent:main:openai-user:{"channel":"dingtalk-connector","accountid":"__default__","chattype":"group","peerid":"cidune9y06rl1j0uelxqielqw==:$:lwcp_v1:$/trkpo9pfvnwbkct3c0b1qnolfh2r8st","conversationid":"cidune9y06rl1j0uelxqielqw==","sendername":"陈江川","groupsubject":"基础设施智能告警"}'


def send_to_dingtalk(message):
    """使用sessions_send发送到钉钉群"""
    import urllib.request
    
    # 调用OpenClaw的API发送消息
    url = "http://127.0.0.1:18789/api/v1/sessions/send"
    
    data = {
        "sessionKey": DINGTALK_SESSION_KEY,
        "message": message,
        "timeoutSeconds": 10
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result.get('status') != 'error'
    except Exception as e:
        print(f"发送失败: {e}")
        # 回退到webhook方式
        return send_via_webhook(message)


def send_via_webhook(message):
    """备用：通过webhook发送"""
    import urllib.request
    
    url = "http://127.0.0.1:18789/hooks/wattrel/wake"
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps({'text': message, 'mode': 'now'}).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer wattrel-webhook-secret-token-2026'
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except:
        return False


def query_alerts():
    """查询昨天到今天的未处理且未恢复告警"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    yesterday_start = f"{yesterday} 00:00:00"
    today_end = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
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
          AND created_at <= ?
          AND status = 0
          AND content NOT LIKE '%已恢复%'
        ORDER BY created_at DESC
    `, ['{yesterday_start}', '{today_end}']);
    await conn.end();
    console.log(JSON.stringify(rows));
}}
query().catch(e => {{ console.error(e); process.exit(1); }});
"""
    
    try:
        result = subprocess.run(['node', '-e', js_code], capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"查询失败: {e}")
    return []


def format_alert(alert):
    """格式化告警"""
    alert_id = alert.get('id')
    content = alert.get('content', '')
    alert_type = alert.get('type', '1')
    created_at = alert.get('created_at')
    
    main_content = content
    sql_content = ''
    if '【执行语句】' in content:
        parts = content.split('【执行语句】', 1)
        main_content = parts[0].strip()
        sql_content = parts[1].strip()
    
    try:
        if isinstance(created_at, str):
            dt = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ')
        else:
            dt = created_at
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        time_str = str(created_at)
    
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
    print("🚀 发送告警到钉钉群（使用sessions_send）")
    print("=" * 70)
    
    # 先发送一条测试消息
    print("\n[测试] 发送测试消息...")
    if send_to_dingtalk("🧪 测试：这是直接发送到钉钉群的消息，请确认是否能收到？"):
        print("✅ 测试消息发送成功")
    else:
        print("❌ 测试消息发送失败")
    
    # 查询告警
    print("\n[*] 查询告警...")
    alerts = query_alerts()
    print(f"[!] 发现 {len(alerts)} 条告警")
    
    if not alerts:
        send_to_dingtalk("🎉 昨天到今天没有新的异常告警，数据质量正常！")
        return
    
    # 逐条发送
    for i, alert in enumerate(alerts, 1):
        msg = format_alert(alert)
        print(f"\n[{i}/{len(alerts)}] 发送告警 ID:{alert['id']}...")
        
        if send_to_dingtalk(msg):
            print("   ✅ 成功")
        else:
            print("   ❌ 失败")
    
    print("\n" + "=" * 70)
    print("✅ 完成")


if __name__ == "__main__":
    main()
