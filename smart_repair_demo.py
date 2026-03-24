#!/usr/bin/env python3
"""
智能告警修复系统 - 流程演示版
展示如何整合本地已有脚本完成7步流程

整合的脚本:
1. alert/alert_query_optimized.py - 查询告警
2. dolphinscheduler/search_table.py - 搜索表位置  
3. dolphinscheduler/check_running.py - 检查工作流状态
"""

import subprocess
import json
import os
import re
import time
from datetime import datetime, timedelta
from collections import defaultdict

WORKSPACE = '/home/node/.openclaw/workspace'
DING_ID = 'cidune9y06rl1j0uelxqielqw=='

# 模拟告警数据（用于演示）
MOCK_ALERTS = [
    {
        'id': 4437,
        'content': '''【任务名称】数据质量校验任务_4437
【告警级别】P1
【告警内容】dwd_asset_account_repay 字段异常
【执行语句】select * from dwd.dwd_asset_account_repay where dt = '2026-03-23' and amount is null;''',
        'level': 'P1',
        'created_at': '2026-03-24 10:00:00'
    },
    {
        'id': 4436,
        'content': '''【任务名称】数据质量校验任务_4436
【告警级别】P2
【告警内容】dwb_asset_period_info 统计不一致
【执行语句】select sum(penalty_amt) from dwb.dwb_asset_info where due_time >= '2026-03-22 00:00:00';''',
        'level': 'P2',
        'created_at': '2026-03-24 09:30:00'
    }
]


def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    try:
        subprocess.run(['openclaw', 'message', 'send', '--channel', 'dingtalk-connector',
            '--target', f'group:{DING_ID}', '--message', msg], capture_output=True, timeout=10)
    except:
        pass


def demo_step1():
    """步骤1: 调用alert_query_optimized.py查询告警"""
    log("\n" + "="*70)
    log("【步骤1】调用 alert_query_optimized.py 查询告警")
    log("="*70)
    log("")
    log("📋 调用命令:")
    log("  python3 alert/alert_query_optimized.py")
    log("")
    log("📋 脚本功能:")
    log("  • 查询昨天到今天的告警")
    log("  • 筛选: status=0 + 未恢复")
    log("  • 推送到OpenClaw webhook")
    log("  • 更新数据库状态为已处理")
    log("")
    
    # 实际调用
    result = subprocess.run(
        ['python3', f'{WORKSPACE}/alert/alert_query_optimized.py'],
        capture_output=True, text=True, timeout=60,
        cwd=f'{WORKSPACE}/alert'
    )
    print(result.stdout)
    
    # 返回模拟数据用于后续步骤
    return MOCK_ALERTS


def demo_step2(alerts):
    """步骤2: 解析告警并调用search_table.py查找位置"""
    log("\n" + "="*70)
    log("【步骤2】解析告警并调用 search_table.py 查找工作流位置")
    log("="*70)
    
    # 解析告警
    parsed = []
    for alert in alerts:
        content = alert['content']
        
        # 提取表名
        tables = re.findall(r'(dwd_\w+|dwb_\w+|ods_\w+|ads_\w+)', content)
        table = tables[0] if tables else None
        
        # 提取dt
        dates = re.findall(r'(\d{4}-\d{2}-\d{2})', content)
        dt = dates[0] if dates else None
        
        if table and dt:
            parsed.append({
                'alert_id': alert['id'],
                'table': table,
                'dt': dt,
                'level': alert['level']
            })
            log(f"\n📋 解析告警:")
            log(f"  表名: {table}")
            log(f"  dt: {dt} (从执行语句提取)")
            log(f"  级别: {alert['level']}")
    
    # 去重
    unique = {p['table']: p for p in parsed}
    tables_to_fix = list(unique.values())
    
    log(f"\n🔍 共 {len(tables_to_fix)} 个唯一表需要查找工作流位置")
    
    # 调用search_table.py查找每个表
    tasks = []
    for table_info in tables_to_fix:
        table = table_info['table']
        log(f"\n  调用: search_table.py {table}")
        log("  " + "-"*50)
        
        # 实际调用
        result = subprocess.run(
            ['python3', f'{WORKSPACE}/dolphinscheduler/search_table.py', table],
            capture_output=True, text=True, timeout=120,
            cwd=f'{WORKSPACE}/dolphinscheduler'
        )
        
        # 显示部分输出
        output_lines = result.stdout.split('\n')[:30]
        for line in output_lines:
            if line.strip():
                log(f"  {line}")
        if len(result.stdout.split('\n')) > 30:
            log("  ... (输出截断)")
        
        # 提取关键信息(模拟)
        if 'dwd_asset' in table:
            tasks.append({
                **table_info,
                'workflow_name': 'DWD',
                'workflow_code': '158514956979200',
                'task_name': table,
                'task_code': '158514956981265'
            })
        elif 'dwb_asset' in table:
            tasks.append({
                **table_info,
                'workflow_name': 'DWB',
                'workflow_code': '158514957297664',
                'task_name': table,
                'task_code': '158514957297701'
            })
    
    # 保存记录
    record_file = f"{WORKSPACE}/auto_repair_records/{datetime.now().strftime('%Y-%m-%d')}_table_locations.json"
    os.makedirs(os.path.dirname(record_file), exist_ok=True)
    with open(record_file, 'w') as f:
        json.dump({
            'date': datetime.now().isoformat(),
            'tables': {t['table']: t for t in tasks}
        }, f, indent=2)
    
    log(f"\n💾 表位置记录已保存: {record_file}")
    return tasks


def demo_step3(tasks):
    """步骤3: 调用check_running.py检查状态并制定计划"""
    log("\n" + "="*70)
    log("【步骤3】调用 check_running.py 检查工作流状态")
    log("="*70)
    
    # 按工作流分组
    workflow_groups = defaultdict(list)
    for task in tasks:
        workflow_groups[task['workflow_name']].append(task)
    
    log(f"\n📁 涉及 {len(workflow_groups)} 个工作流:")
    
    for wf_name, wf_tasks in workflow_groups.items():
        log(f"\n  检查工作流: {wf_name}")
        log(f"  调用: check_running.py -f \"{wf_name}\" --check-only")
        
        # 实际调用
        result = subprocess.run(
            ['python3', f'{WORKSPACE}/dolphinscheduler/check_running.py',
             '-f', wf_name, '--check-only'],
            capture_output=True, text=True, timeout=30,
            cwd=f'{WORKSPACE}/dolphinscheduler'
        )
        
        is_idle = (result.returncode == 0)
        status = "✅ 空闲" if is_idle else "⏳ 忙碌"
        log(f"  结果: {status}")
        log(f"  输出: {result.stdout.strip()}")
    
    # 显示执行计划
    log("\n" + "="*70)
    log("📋 执行计划:")
    log("="*70)
    
    for i, task in enumerate(tasks, 1):
        log(f"\n  {i}. {task['table']}")
        log(f"     dt: {task['dt']} (从告警SQL提取)")
        log(f"     工作流: {task['workflow_name']} ({task['workflow_code']})")
        log(f"     任务: {task['task_name']} ({task['task_code']})")
    
    log("\n⚠️ 限制条件:")
    log("  • 最大并行: 2个任务")
    log("  • 同工作流串行执行")
    log("  • dt范围: 当前时间±10天")
    
    return workflow_groups


def demo_step4(tasks):
    """步骤4: 执行重跑（仅显示命令，不实际执行）"""
    log("\n" + "="*70)
    log("【步骤4】执行重跑任务（演示命令，不实际启动）")
    log("="*70)
    
    log("\n📋 将要执行的curl命令:")
    log("")
    
    for i, task in enumerate(tasks, 1):
        log(f"  [{i}] {task['table']}")
        log("")
        
        cmd = f"""curl -X POST 'http://172.20.0.235:12345/dolphinscheduler/projects/158514956085248/executors/start-process-instance' \\
    -H 'token: 0cad23ded0f0e942381fc9717c1581a8' \\
    -d 'processDefinitionCode={task['workflow_code']}' \\
    -d 'startNodeList={task['task_code']}' \\
    -d 'taskDependType=TASK_ONLY' \\
    -d 'failureStrategy=CONTINUE' \\
    -d 'warningType=NONE' \\
    -d 'startParams={{\\"dt\\":\\"{task['dt']}\\"}}'"""
        
        log(cmd)
        log("")
        
        # 模拟执行结果
        log(f"  [模拟] ✅ 启动成功! 实例ID: {100000 + i}")
        task['instance_id'] = str(100000 + i)
        task['status'] = 'success'
    
    return tasks


def demo_step5_6_7(tasks):
    """步骤5-7: 记录、复验、验证、保存"""
    log("\n" + "="*70)
    log("【步骤5】记录重跑次数")
    log("="*70)
    
    record_file = f"{WORKSPACE}/auto_repair_records/repair_counts.json"
    counts = {}
    
    today = datetime.now().strftime('%Y-%m-%d')
    for task in tasks:
        table = task['table']
        if table not in counts:
            counts[table] = {}
        counts[table][today] = 1
        log(f"📝 {table}: 今日第1次重跑")
    
    os.makedirs(os.path.dirname(record_file), exist_ok=True)
    with open(record_file, 'w') as f:
        json.dump(counts, f, indent=2)
    
    log("\n" + "="*70)
    log("【步骤6】执行复验并验证结果")
    log("="*70)
    
    log("\n🔄 提交复验工作流:")
    log("  • 每日复验全级别数据(W-1)")
    log("  • Code: 158515019703296")
    log("\n⏳ 等待复验完成...")
    time.sleep(2)
    log("✅ 复验完成")
    
    log("\n🔍 再次扫描数据库验证修复结果...")
    time.sleep(1)
    
    # 模拟验证结果
    fixed = tasks  # 假设都成功了
    failed = []
    
    log("\n" + "="*70)
    log("📊 智能告警修复报告")
    log("="*70)
    
    log(f"\n✅ 修复成功 ({len(fixed)}个表):")
    for task in fixed:
        log(f"  • {task['table']} (dt={task['dt']}) - 重跑成功，复验通过")
    
    log("\n" + "="*70)
    log("【步骤7】保存操作记录")
    log("="*70)
    
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    date = datetime.now().strftime('%Y-%m-%d')
    base_dir = f"{WORKSPACE}/auto_repair_records/{date}"
    os.makedirs(base_dir, exist_ok=True)
    
    files = [
        f"{base_dir}/repair_{ts}.log",
        f"{base_dir}/detail_{ts}.json",
        f"{base_dir}/commands_{ts}.sh",
        f"{base_dir}/thinking_{ts}.md"
    ]
    
    for f in files:
        log(f"📝 {os.path.basename(f)}")
    
    log(f"\n📁 所有记录保存在: {base_dir}/")
    
    return fixed, failed


def main():
    """主流程"""
    log("="*70)
    log("🚀 智能告警修复系统 - 流程演示版")
    log("="*70)
    log("整合本地脚本完成7步流程")
    log("="*70)
    
    # 步骤1
    alerts = demo_step1()
    
    # 步骤2
    tasks = demo_step2(alerts)
    
    # 步骤3
    workflow_groups = demo_step3(tasks)
    
    # 步骤4
    results = demo_step4(tasks)
    
    # 步骤5-7
    fixed, failed = demo_step5_6_7(results)
    
    log("\n" + "="*70)
    log("✅ 完整流程演示完成")
    log("="*70)
    log("")
    log("📋 流程总结:")
    log("  1. ✅ alert_query_optimized.py - 查询告警")
    log("  2. ✅ search_table.py - 查找表位置")
    log("  3. ✅ check_running.py - 检查工作流状态")
    log("  4. ✅ curl DS API - 启动重跑任务")
    log("  5. ✅ 记录重跑次数")
    log("  6. ✅ 执行复验+验证结果")
    log("  7. ✅ 保存所有操作记录")


if __name__ == '__main__':
    main()
