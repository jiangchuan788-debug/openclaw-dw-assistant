#!/usr/bin/env python3
"""
智能告警修复 - 生产环境版本 (v4.1)
真实调用API，异步执行（不等任务完成）
参考v2.8的执行逻辑

作者: OpenClaw
日期: 2026-03-26
"""

import sys
sys.path.insert(0, '/home/node/.openclaw/workspace')
from config import auto_load_env

import json
import os
import urllib.request
import time
from datetime import datetime
from urllib.parse import urlencode

# 配置
WORKSPACE = '/home/node/.openclaw/workspace'
DS_BASE = 'http://172.20.0.235:12345/dolphinscheduler'
PROJECT_CODE = '158514956085248'
FUYAN_PROJECT_CODE = '158515019231232'
DS_TOKEN = os.environ.get('DS_TOKEN', '')

# 复验工作流
FUYAN_WORKFLOWS = [
    {'name': '每日复验全级别数据(W-1)', 'code': '158515019703296', 'level': 'all'},
    {'name': '每小时复验1级表数据(D-1)', 'code': '158515019593728', 'level': '1'},
    {'name': '两小时复验3级表数据(D-1)', 'code': '158515019667456', 'level': '3'},
]


def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{ts}] {msg}")


def ds_api_get(endpoint):
    """DS API GET 请求"""
    url = f"{DS_BASE}{endpoint}"
    req = urllib.request.Request(url)
    req.add_header('token', DS_TOKEN)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('code') == 0, result.get('data', {}), result.get('msg', '')
    except Exception as e:
        return False, {}, str(e)


def ds_api_post(endpoint, data):
    """DS API POST 请求 - form-data格式"""
    url = f"{DS_BASE}{endpoint}"
    encoded_data = urlencode(data).encode('utf-8')
    req = urllib.request.Request(
        url, data=encoded_data,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST'
    )
    req.add_header('token', DS_TOKEN)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('code') == 0, result, result.get('msg', '')
    except Exception as e:
        return False, {}, str(e)


def step1_scan_alerts():
    """步骤1: 扫描告警 - 从 wattrel_quality_result 表"""
    log("="*70)
    log("【步骤1】扫描告警 - 从 wattrel_quality_result 表")
    log("="*70)
    
    alerts = []
    try:
        from alert.db_config import get_db_connection
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
                SELECT id, name, src_db, src_tbl, dest_db, dest_tbl, `begin`, diff
                FROM wattrel_quality_result
                WHERE result = 1 AND is_repaired = 0
                  AND created_at >= DATE_SUB(NOW(), INTERVAL 3 DAY)
                ORDER BY created_at DESC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            for row in rows:
                # 优先选择DWD/DWB层的目标表
                dest_db = row.get('dest_db') or ''
                dest_tbl = row.get('dest_tbl') or ''
                src_db = row.get('src_db') or ''
                src_tbl = row.get('src_tbl') or ''
                
                if dest_db.lower() in ['dwd', 'dwb', 'ads'] and dest_tbl:
                    table_name = dest_tbl
                elif src_db.lower() in ['dwd', 'dwb', 'ads'] and src_tbl:
                    table_name = src_tbl
                else:
                    table_name = dest_tbl or src_tbl
                
                begin_time = row.get('begin')
                if begin_time:
                    dt = begin_time.strftime('%Y-%m-%d') if hasattr(begin_time, 'strftime') else str(begin_time).split()[0]
                else:
                    dt = datetime.now().strftime('%Y-%m-%d')
                
                alerts.append({
                    'id': row['id'],
                    'table': table_name,
                    'dt': dt,
                    'name': row.get('name', ''),
                    'diff': row.get('diff', '')
                })
        
        conn.close()
        log(f"✅ 从 wattrel_quality_result 表查询到 {len(alerts)} 条异常记录")
        
    except Exception as e:
        log(f"❌ 查询数据库失败: {e}")
        return []
    
    # 去重
    table_alerts = {}
    for alert in alerts:
        table = alert['table']
        if table and table not in table_alerts:
            table_alerts[table] = alert
    
    unique_alerts = list(table_alerts.values())
    log(f"\n📊 扫描结果: {len(unique_alerts)} 个（去重后）")
    for alert in unique_alerts:
        log(f"  ✅ {alert['table']} (dt={alert['dt']})")
    
    return unique_alerts


def search_table_in_workflows(table_name):
    """在所有工作流中搜索表名"""
    success, data, msg = ds_api_get(f"/projects/{PROJECT_CODE}/process-definition?pageNo=1&pageSize=100")
    if not success:
        return None
    
    workflows = data.get('totalList', [])
    
    for wf in workflows:
        process_code = wf.get('code')
        process_name = wf.get('name', '')
        
        # 获取工作流详情
        s, detail, m = ds_api_get(f"/projects/{PROJECT_CODE}/process-definition/{process_code}")
        if not s:
            continue
        
        tasks = detail.get('taskDefinitionList', [])
        for task in tasks:
            task_params = task.get('taskParams', {})
            if isinstance(task_params, str):
                try:
                    task_params = json.loads(task_params)
                except:
                    task_params = {}
            
            sql = task_params.get('sql', '')
            if sql and table_name.lower() in sql.lower():
                return {
                    'workflow_code': process_code,
                    'workflow_name': process_name,
                    'task_code': task.get('code'),
                    'task_name': task.get('name')
                }
    
    return None


def step2_find_locations(alerts):
    """步骤2: 查找工作流位置"""
    log("\n" + "="*70)
    log("【步骤2】查找工作流位置")
    log("="*70)
    
    tasks = []
    for alert in alerts:
        table = alert['table']
        log(f"  🔍 查找: {table}")
        
        location = search_table_in_workflows(table)
        if location:
            task = {
                'alert_id': alert['id'],
                'table': table,
                'dt': alert['dt'],
                'workflow_code': location['workflow_code'],
                'workflow_name': location['workflow_name'],
                'task_code': location['task_code'],
                'task_name': location['task_name']
            }
            log(f"    ✅ 找到: {location['workflow_name']} -> {location['task_name']}")
        else:
            task = {
                'alert_id': alert['id'],
                'table': table,
                'dt': alert['dt'],
                'workflow_code': '',
                'workflow_name': '未找到',
                'task_code': '',
                'task_name': ''
            }
            log(f"    ❌ 未找到")
        
        tasks.append(task)
    
    return tasks


def start_task_only(workflow_code, task_code, dt):
    """启动特定任务（TASK_ONLY模式）"""
    data = {
        'processDefinitionCode': workflow_code,
        'startNodeList': task_code,
        'taskDependType': 'TASK_ONLY',
        'failureStrategy': 'CONTINUE',
        'warningType': 'NONE',
        'warningGroupId': 0,
        'execType': 'START_PROCESS',
        'startParams': json.dumps({'global': [{'prop': 'dt', 'value': dt}]}),
        'environmentCode': 154818922491872,
        'tenantCode': 'dolphinscheduler',
        'dryRun': 0,
        'scheduleTime': ''
    }
    
    success, result, msg = ds_api_post(f"/projects/{PROJECT_CODE}/executors/start-process-instance", data)
    return success, result


def step3_execute_with_limits(tasks):
    """步骤3: 执行修复"""
    log("\n" + "="*70)
    log("【步骤3】执行修复")
    log("="*70)
    
    results = []
    processed_tables = set()
    
    for i, task in enumerate(tasks, 1):
        table = task['table']
        dt = task['dt']
        workflow_code = task.get('workflow_code')
        task_code = task.get('task_code')
        
        if not workflow_code or not task_code:
            log(f"[{i}/{len(tasks)}] ⏭️ {table} - 未找到工作流，跳过")
            task['status'] = 'skipped_no_workflow'
            results.append(task)
            continue
        
        if table in processed_tables:
            log(f"[{i}/{len(tasks)}] ⏭️ {table} - 已修复，跳过")
            task['status'] = 'skipped_duplicate'
            results.append(task)
            continue
        
        log(f"\n[{i}/{len(tasks)}] {table}")
        log(f"  dt: {dt}")
        log(f"  工作流: {task.get('workflow_name')}")
        
        # dt范围检查
        try:
            dt_date = datetime.strptime(dt, '%Y-%m-%d')
            if abs((dt_date - datetime.now()).days) > 10:
                log(f"  ❌ dt超出范围，跳过")
                task['status'] = 'skipped_dt_range'
                results.append(task)
                continue
        except:
            pass
        
        # 启动修复
        log(f"  🔄 启动修复任务...")
        success, result = start_task_only(workflow_code, task_code, dt)
        
        if success:
            instance_id = result.get('data', 'unknown')
            log(f"  ✅ 启动成功，实例ID: {instance_id}")
            task['status'] = 'success'
            task['instance_id'] = instance_id
            processed_tables.add(table)
        else:
            error_msg = result.get('msg', '未知错误')
            log(f"  ❌ 启动失败: {error_msg}")
            task['status'] = 'failed'
            task['error'] = error_msg
        
        results.append(task)
        time.sleep(2)
    
    return results


def start_fuyan_workflow(workflow_code):
    """启动复验工作流"""
    data = {
        'processDefinitionCode': workflow_code,
        'failureStrategy': 'CONTINUE',
        'warningType': 'NONE',
        'warningGroupId': 0,
        'execType': 'START_PROCESS',
        'environmentCode': 154818922491872,
        'tenantCode': 'dolphinscheduler',
        'dryRun': 0,
        'scheduleTime': ''
    }
    
    success, result, msg = ds_api_post(f"/projects/{FUYAN_PROJECT_CODE}/executors/start-process-instance", data)
    return success, result


def step4_record_and_fuyan(results, alerts=None):
    """步骤4: 记录+复验（异步，不等完成）"""
    log("\n" + "="*70)
    log("【步骤4】记录重跑次数 + 执行复验")
    log("="*70)
    
    # 4.1 记录重跑次数
    log("\n4.1 记录重跑次数...")
    record_file = f"{WORKSPACE}/auto_repair_records/repair_counts.json"
    counts = {}
    if os.path.exists(record_file):
        with open(record_file, 'r') as f:
            counts = json.load(f)
    
    today = datetime.now().strftime('%Y-%m-%d')
    for task in results:
        if task.get('status') == 'success':
            table = task['table']
            if table not in counts:
                counts[table] = {}
            counts[table][today] = counts[table].get(today, 0) + 1
            log(f"  📝 {table}: 今日第{counts[table][today]}次")
    
    with open(record_file, 'w') as f:
        json.dump(counts, f, indent=2)
    
    # 4.2 执行复验（异步启动，不等完成）
    # 智能选择复验工作流
    selected_codes = {'158515019703296'}  # 每日全级别必跑
    for alert in alerts or []:
        table = alert.get('table', '')
        if table.startswith('dwb_'):
            selected_codes.add('158515019593728')  # 1级表
        else:
            selected_codes.add('158515019667456')  # 3级表
    
    fuyan_workflows = [wf for wf in FUYAN_WORKFLOWS if wf['code'] in selected_codes]
    fuyan_results = []
    
    log(f"\n4.2 执行复验工作流 (共{len(fuyan_workflows)}个)...")
    for i, fuyan in enumerate(fuyan_workflows, 1):
        log(f"  [{i}] {fuyan['name']}")
        success, result = start_fuyan_workflow(fuyan['code'])
        if success:
            instance_id = result.get('data', 'unknown')
            log(f"    ✅ 启动成功，实例ID: {instance_id}")
            fuyan_results.append({'name': fuyan['name'], 'id': instance_id, 'status': 'success'})
        else:
            error_msg = result.get('msg', '未知错误')
            log(f"    ❌ 启动失败: {error_msg}")
            fuyan_results.append({'name': fuyan['name'], 'status': 'failed', 'error': error_msg})
    
    # 不等复验完成，直接返回
    log("\n4.3 复验工作流已启动（异步执行）")
    return fuyan_results


def step5_save_report(results, fuyan_results):
    """步骤5: 保存记录"""
    log("\n" + "="*70)
    log("【步骤5】保存记录")
    log("="*70)
    
    fixed = [r for r in results if r.get('status') == 'success']
    failed = [r for r in results if r.get('status') != 'success']
    
    log(f"  修复成功: {len(fixed)} 个")
    log(f"  修复失败/跳过: {len(failed)} 个")
    
    # 保存记录
    record_dir = f"{WORKSPACE}/auto_repair_records/{datetime.now().strftime('%Y-%m-%d')}"
    os.makedirs(record_dir, exist_ok=True)
    
    detail_file = f"{record_dir}/detail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(detail_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'fuyan_results': fuyan_results,
            'fixed_count': len(fixed),
            'failed_count': len(failed)
        }, f, indent=2, ensure_ascii=False)
    
    log(f"  ✅ 记录已保存: {detail_file}")
    
    return fixed, failed


def main():
    """主函数"""
    log("="*70)
    log("🚀 智能告警修复流程（生产环境版本 v4.1）")
    log("="*70)
    log(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("")
    
    # 步骤1: 扫描告警
    alerts = step1_scan_alerts()
    if not alerts:
        log("\n✅ 没有需要处理的告警，流程结束")
        return
    
    # 步骤2: 查找工作流
    tasks = step2_find_locations(alerts)
    
    # 步骤3: 执行修复
    results = step3_execute_with_limits(tasks)
    
    # 步骤4: 记录+复验
    fuyan_results = step4_record_and_fuyan(results, alerts)
    
    # 步骤5: 保存记录
    fixed, failed = step5_save_report(results, fuyan_results)
    
    log("\n" + "="*70)
    log("✅ 流程完成")
    log("="*70)
    log(f"\n📊 最终统计:")
    log(f"  扫描告警: {len(alerts)} 个")
    log(f"  修复成功: {len(fixed)} 个")
    log(f"  失败/跳过: {len(failed)} 个")
    log(f"  执行复验: {len(fuyan_results)} 个")


if __name__ == '__main__':
    main()
