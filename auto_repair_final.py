#!/usr/bin/env python3
"""
完全动态修复系统 - 无硬编码
CSV搜索 → 任务搜索 → 解析dt → 执行单任务
"""

import csv
import json
import subprocess
import re
from datetime import datetime

CSV_FILE = '/home/node/.openclaw/workspace/dolphinscheduler/workflows_export.csv'
DS_BASE = 'http://172.20.0.235:12345/dolphinscheduler'
DS_TOKEN = '0cad23ded0f0e942381fc9717c1581a8'
PROJECT = '158514956085248'
DING = 'cidune9y06rl1j0uelxqielqw=='

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    try:
        subprocess.run(['openclaw', 'message', 'send', '--channel', 'dingtalk-connector', '--target', f'group:{DING}', '--message', msg], capture_output=True, timeout=10)
    except:
        pass

def search_csv(table):
    """从CSV搜索工作流 - 返回所有同类型的工作流列表"""
    log(f"🔍 CSV搜索: {table}")
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    
    # 根据表前缀确定工作流类型
    table_lower = table.lower()
    if table_lower.startswith('dwd_'):
        wf_type = 'DWD'
    elif table_lower.startswith('dwb_'):
        wf_type = 'DWB'
    elif table_lower.startswith('ods_'):
        wf_type = 'ODS'
    elif table_lower.startswith('ads_'):
        wf_type = 'ADS'
    else:
        wf_type = None
    
    log(f"  📋 表前缀推断工作流类型: {wf_type}")
    
    # 收集所有同类型的ONLINE工作流
    matched = []
    if wf_type:
        for row in rows:
            name = row.get('工作流名称', '')
            status = row.get('状态', '')
            if wf_type in name and status == 'ONLINE':
                matched.append(row)
                log(f"  📋 找到: {name} ({row.get('工作流Code')})")
    
    # 如果没有类型匹配，用关键字匹配
    if not matched:
        parts = table.split('_')
        keywords = [parts[2], '_'.join(parts[2:]), parts[-1]] if len(parts) >= 3 else [table]
        for row in rows:
            name = row.get('工作流名称', '')
            status = row.get('状态', '')
            if status != 'ONLINE':
                continue
            for kw in keywords:
                if kw.lower() in name.lower():
                    matched.append(row)
                    break
    
    return matched  # 返回列表，不是一个

def search_task(wf_code, table):
    """在工作流内搜索任务"""
    log(f"🔍 搜索任务 (WF: {wf_code})")
    cmd = f"curl -s '{DS_BASE}/projects/{PROJECT}/process-definition/{wf_code}' -H 'token: {DS_TOKEN}'"
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
    
    if r.returncode != 0:
        return None
    
    data = json.loads(r.stdout)
    if data.get('code') != 0:
        return None
    
    tasks = data['data'].get('taskDefinitionList', [])
    for task in tasks:
        name = task.get('name', '')
        tcode = task.get('code')
        params = task.get('taskParams', '{}')
        
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except:
                params = {}
        
        sql = params.get('rawScript', '') if isinstance(params, dict) else ''
        
        if table.lower() in sql.lower():
            log(f"  ✅ SQL匹配: {name}")
            return {'code': tcode, 'name': name}
        
        parts = table.split('_')
        if len(parts) >= 3:
            key = '_'.join(parts[2:])
            if key.lower() in name.lower():
                log(f"  ✅ 名称匹配: {name}")
                return {'code': tcode, 'name': name}
    
    return None

def parse_dt(content):
    """从告警解析dt"""
    m = re.findall(r'(\d{4}-\d{2}-\d{2})', content)
    return m[0] if m else None

def start_task(wf_code, task_code, name, table, dt):
    """启动单任务"""
    log(f"🚀 启动: {name} ({table}, dt={dt})")
    cmd = f"curl -s -X POST '{DS_BASE}/projects/{PROJECT}/executors/start-process-instance' -H 'token: {DS_TOKEN}' -d 'processDefinitionCode={wf_code}' -d 'startNodeList={task_code}' -d 'taskDependType=TASK_ONLY' -d 'startParams={{\"dt\":\"{dt}\"}}' --connect-timeout 30"
    
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=35)
    
    if r.returncode == 0:
        resp = json.loads(r.stdout)
        if resp.get('code') == 0:
            log(f"✅ 成功! ID: {resp.get('data')}")
            return True
        else:
            log(f"❌ 失败: {resp.get('msg')}")
    else:
        log(f"❌ 请求失败")
    return False

def main():
    log("=" * 50)
    log("🚀 完全动态修复系统")
    log("=" * 50)
    
    table = 'dwd_asset_account_repay'
    content = "SELECT * FROM dwd.dwd_asset_account_repay WHERE dt = '2026-03-23'"
    
    log(f"\n📋 表: {table}")
    
    # 步骤1: CSV搜索 - 获取所有同类型工作流
    workflows = search_csv(table)
    if not workflows:
        log("❌ CSV未找到工作流")
        return
    
    log(f"\n📁 找到 {len(workflows)} 个候选工作流，逐个搜索任务...")
    
    # 步骤2: 在每个工作流中搜索任务
    task = None
    wf_code = None
    wf_name = None
    
    for wf in workflows:
        wf_code = wf.get('工作流Code')
        wf_name = wf.get('工作流名称')
        log(f"\n  检查工作流: {wf_name}")
        
        task = search_task(wf_code, table)
        if task:
            log(f"  ✅ 在工作流 {wf_name} 中找到任务")
            break
    
    if not task:
        log("❌ 所有工作流中均未找到任务")
        return
    
    log(f"🔧 任务: {task['name']} ({task['code']})")
    
    # 步骤3: 解析dt
    dt = parse_dt(content)
    if not dt:
        log("❌ dt解析失败")
        return
    
    log(f"📅 dt: {dt}")
    
    # 步骤4: 启动任务
    log(f"\n{'='*50}")
    start_task(wf_code, task['code'], task['name'], table, dt)
    log(f"{'='*50}")

if __name__ == '__main__':
    main()
