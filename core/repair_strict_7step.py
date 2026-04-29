#!/usr/bin/env python3
"""
智能告警修复 - v5.2 最终修复版
修复问题:
1. 步骤2执行完成的准确判断
2. 步骤4状态检查不显示详细状态的问题
3. API查询失败时的错误处理

作者: OpenClaw
日期: 2026-03-27
"""

import sys
sys.path.insert(0, '/home/node/.openclaw/workspace')
from config import auto_load_env

import json
import os
import urllib.request
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode

# 配置
WORKSPACE = '/home/node/.openclaw/workspace'
DS_BASE = 'http://172.20.0.235:12345/dolphinscheduler'
PROJECT_CODE = '158514956085248'
FUYAN_PROJECT_CODE = '158515019231232'
DS_TOKEN = '72b6ff29a6484039a1ddd3f303973505'
MANUAL_REVIEW_STATE_FILE = f"{WORKSPACE}/auto_repair_records/manual_review_state.json"

# 复验工作流
FUYAN_WORKFLOWS = [
    {'name': '每日复验全级别数据(W-1)', 'code': '158515019703296', 'level': 'all'},
    {'name': '两小时复验3级表数据(D-1)', 'code': '158515019667456', 'level': '3'},
]

# 维护任务关键词（排除）
MAINTENANCE_KEYWORDS = ['补充', '删除', '清理', '修复', '历史', '冗余', '临时', 'test', 'copy', '手插入']


def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{ts}] {msg}", flush=True)


def ds_api_get(endpoint):
    """DS API GET请求"""
    url = f"{DS_BASE}{endpoint}"
    req = urllib.request.Request(url)
    req.add_header('token', DS_TOKEN)
    req.add_header('Accept', 'application/json, text/plain, */*')
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('code') == 0, result.get('data', {}), result.get('msg', '')
    except Exception as e:
        return False, {}, str(e)


def ds_api_post(endpoint, data):
    """DS API POST请求"""
    url = f"{DS_BASE}{endpoint}"
    encoded_data = urlencode(data).encode('utf-8')
    req = urllib.request.Request(
        url, data=encoded_data,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST'
    )
    req.add_header('token', DS_TOKEN)
    req.add_header('Accept', 'application/json, text/plain, */*')
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('code') == 0, result, result.get('msg', '')
    except Exception as e:
        return False, {}, str(e)


def normalize_to_datetime(value):
    """将数据库中的时间字段尽量标准化为 datetime"""
    if not value:
        return None

    if hasattr(value, 'strftime'):
        return value

    text = str(value).strip()
    for pattern in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S.%fZ'):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


def resolve_alert_dt(row, now=None):
    """解析告警对应的修复 dt，优先 begin，其次 end-1 天，最后兜底当天"""
    if now is None:
        now = datetime.now()

    begin_time = normalize_to_datetime(row.get('begin'))
    if begin_time:
        return begin_time.strftime('%Y-%m-%d')

    end_time = normalize_to_datetime(row.get('end'))
    if end_time:
        return (end_time - timedelta(days=1)).strftime('%Y-%m-%d')

    return now.strftime('%Y-%m-%d')


def step1_scan_alerts():
    """步骤1: 扫描告警"""
    log("="*70)
    log("【步骤1】扫描告警")
    log("="*70)
    
    alerts = []
    try:
        from alert.db_config import get_db_connection
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
                SELECT id, name, src_db, src_tbl, dest_db, dest_tbl, `begin`, `end`, diff
                FROM wattrel_quality_result
                WHERE result = 1 AND is_repaired = 0
                  AND created_at >= DATE_SUB(NOW(), INTERVAL 3 DAY)
                ORDER BY created_at DESC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            for row in rows:
                dest_db = row.get('dest_db') or ''
                dest_tbl = row.get('dest_tbl') or ''
                
                if dest_db.lower() in ['dwd', 'dwb', 'ads'] and dest_tbl:
                    table_name = dest_tbl
                else:
                    table_name = row.get('src_tbl') or ''
                
                dt = resolve_alert_dt(row)
                
                alerts.append({
                    'id': row['id'],
                    'table': table_name,
                    'dt': dt,
                    'name': row.get('name', ''),
                    'diff': row.get('diff', '')
                })
        
        conn.close()
        log(f"✅ 查询到 {len(alerts)} 条异常记录")
        
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
    log(f"📊 去重后: {len(unique_alerts)} 个")
    for alert in unique_alerts[:5]:  # 只显示前5个
        log(f"  ✅ {alert['table']} (dt={alert['dt']})")
    if len(unique_alerts) > 5:
        log(f"  ... 还有 {len(unique_alerts)-5} 个")
    
    return unique_alerts


def step2_search_in_workflow(workflow_code, table_name):
    """在指定工作流中搜索表"""
    success, detail, msg = ds_api_get(f"/projects/{PROJECT_CODE}/workflow-definition/{workflow_code}")
    if not success:
        return None
    
    search_term = table_name.lower().replace('dwd_', '').replace('dwb_', '').replace('ods_', '')
    tasks = detail.get('taskDefinitionList', [])
    
    for task in tasks:
        task_name = task.get('name', '')
        task_name_lower = task_name.lower()
        
        # 排除维护任务
        is_maintenance = any(kw in task_name_lower for kw in MAINTENANCE_KEYWORDS)
        if is_maintenance:
            continue
        
        # 匹配任务名
        if search_term in task_name_lower:
            return {
                'workflow_code': workflow_code,
                'workflow_name': detail.get('processDefinition', {}).get('name', ''),
                'task_code': task.get('code'),
                'task_name': task_name
            }
        
        # 匹配SQL
        task_params = task.get('taskParams', '{}')
        if isinstance(task_params, str):
            try:
                task_params = json.loads(task_params)
            except:
                task_params = {}
        
        sql = task_params.get('sql', '').lower()
        if search_term in sql:
            return {
                'workflow_code': workflow_code,
                'workflow_name': detail.get('processDefinition', {}).get('name', ''),
                'task_code': task.get('code'),
                'task_name': task_name
            }
    
    return None


def step2_find_locations(alerts):
    """步骤2: 查找工作流位置 - 优化版（缓存工作流列表）"""
    log("\n" + "="*70)
    log("【步骤2】查找工作流位置")
    log("="*70)
    
    # 优先搜索这些工作流（提高效率）
    priority_workflows = [
        ('158514956979200', 'DWD'),
        ('158514957656064', 'DWD(D-1)'),
        ('158514958374912', '国内-数仓工作流(H-1)'),
        ('158514957337600', '国内-数仓工作流(D-1)'),
        ('158514957297664', 'DWB'),
        ('158514957701120', 'DWB(D-1)'),
        ('158514957779968', 'DWS'),
        ('158514958004224', 'DWS(D-1)'),
    ]
    
    # 缓存所有工作流列表（只获取一次）
    all_workflows = None
    
    tasks = []
    found_count = 0
    
    for alert in alerts:
        table = alert['table']
        log(f"🔍 {table}")
        
        location = None
        # 先在优先工作流中搜索
        for wf_code, wf_name in priority_workflows:
            result = step2_search_in_workflow(wf_code, table)
            if result:
                location = result
                break
        
        # 如果没找到，再搜索所有工作流（使用缓存）
        if not location:
            if all_workflows is None:
                log(f"  在优先工作流中未找到，获取所有工作流列表...")
                success, data, msg = ds_api_get(f"/projects/{PROJECT_CODE}/workflow-definition?pageNo=1&pageSize=100")
                if success:
                    all_workflows = data.get('totalList', [])
                    log(f"  获取到 {len(all_workflows)} 个工作流")
                else:
                    log(f"  ❌ 获取工作流列表失败: {msg}")
                    all_workflows = []
            
            # 在缓存的工作流中搜索
            for wf in all_workflows:
                wf_code = wf.get('code')
                # 跳过已在priority中搜索过的工作流
                if wf_code not in [pw[0] for pw in priority_workflows]:
                    result = step2_search_in_workflow(wf_code, table)
                    if result:
                        location = result
                        break
        
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
            log(f"  ✅ {location['workflow_name']} -> {location['task_name']}")
            found_count += 1
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
            log(f"  ❌ 未找到")
        
        tasks.append(task)
    
    log(f"\n📊 找到 {found_count}/{len(alerts)} 个工作流")
    return tasks


def load_manual_review_state():
    """加载人工处理策略状态"""
    if not os.path.exists(MANUAL_REVIEW_STATE_FILE):
        return {}

    try:
        with open(MANUAL_REVIEW_STATE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        log(f"⚠️ 读取人工处理状态失败: {e}")
        return {}


def save_manual_review_state(state):
    """保存人工处理策略状态"""
    os.makedirs(os.path.dirname(MANUAL_REVIEW_STATE_FILE), exist_ok=True)
    with open(MANUAL_REVIEW_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def is_suspected_redundant_data(task):
    """根据 diff 判断是否为疑似冗余数据告警"""
    diff = task.get('diff')
    if diff in (None, ''):
        return False

    try:
        return float(diff) < 0
    except (TypeError, ValueError):
        return False


def apply_repair_strategy(tasks, strategy_state):
    """应用修复策略：疑似冗余数据仅允许自动重跑一次"""
    runnable_tasks = []
    manual_review_tasks = []

    for task in tasks:
        if not is_suspected_redundant_data(task):
            runnable_tasks.append(task)
            continue

        table_state = strategy_state.get(task['table'], {}).get(task['dt'], {})
        if table_state.get('redundant_retry_done'):
            manual_task = dict(task)
            manual_task['status'] = 'skipped_manual_review'
            manual_task['error'] = '疑似冗余数据，已重跑一次仍未恢复，转人工处理'
            manual_review_tasks.append(manual_task)
        else:
            runnable_tasks.append(task)

    return runnable_tasks, manual_review_tasks


def record_redundant_retry_attempt(strategy_state, completed_tasks):
    """记录疑似冗余数据告警的首次自动重跑尝试"""
    for task in completed_tasks:
        if not is_suspected_redundant_data(task):
            continue

        table_state = strategy_state.setdefault(task['table'], {})
        dt_state = table_state.setdefault(task['dt'], {})
        dt_state['redundant_retry_done'] = True
        dt_state.setdefault('manual_review_required', False)
        dt_state['last_completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def record_manual_review_tasks(strategy_state, manual_review_tasks):
    """记录需要人工处理的任务状态"""
    for task in manual_review_tasks:
        table_state = strategy_state.setdefault(task['table'], {})
        dt_state = table_state.setdefault(task['dt'], {})
        dt_state['redundant_retry_done'] = True
        dt_state['manual_review_required'] = True
        dt_state['reason'] = task.get('error', '需人工处理')
        dt_state['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def step3_start_repair(tasks):
    """步骤3: 启动修复任务"""
    log("\n" + "="*70)
    log("【步骤3】启动修复任务")
    log("="*70)
    
    results = []
    running_instances = []
    
    for i, task in enumerate(tasks, 1):
        table = task['table']
        dt = task['dt']
        workflow_code = task.get('workflow_code')
        task_code = task.get('task_code')
        
        if not workflow_code or not task_code:
            log(f"[{i}/{len(tasks)}] ⏭️ {table} - 未找到工作流")
            task['status'] = 'skipped_no_workflow'
            results.append(task)
            continue
        
        log(f"\n[{i}/{len(tasks)}] {table}")
        log(f"  工作流: {task['workflow_name']}")
        log(f"  任务: {task['task_name']}")
        
        # 启动修复
        schedule_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'workflowDefinitionCode': workflow_code,
            'startNodeList': task_code,
            'taskDependType': 'TASK_ONLY',
            'failureStrategy': 'CONTINUE',
            'warningType': 'NONE',
            'warningGroupId': 0,
            'execType': 'START_PROCESS',
            'startParams': f'[{{"prop":"dt","value":"{dt}"}}]',
            'environmentCode': 154818922491872,
            'tenantCode': 'dolphinscheduler',
            'dryRun': 0,
            'scheduleTime': schedule_time
        }
        
        success, result, msg = ds_api_post(f"/projects/{PROJECT_CODE}/executors/start-workflow-instance", data)
        
        if success:
            instance_data = result.get('data')
            # DS 3.3.0 返回的是数组格式 [id]，需要取第一个元素
            if isinstance(instance_data, list) and len(instance_data) > 0:
                instance_id = instance_data[0]
            else:
                instance_id = instance_data
            log(f"  ✅ 启动成功，实例ID: {instance_id}")
            task['status'] = 'success'
            task['instance_id'] = instance_id
            running_instances.append({
                'table': table,
                'instance_id': instance_id,
                'task': task
            })
        else:
            error_msg = result.get('msg', '未知错误')
            log(f"  ❌ 启动失败: {error_msg}")
            task['status'] = 'failed'
            task['error'] = error_msg
        
        results.append(task)
        time.sleep(1)
    
    log(f"\n📊 启动结果: {len(running_instances)} 个成功, {len(tasks) - len(running_instances)} 个跳过/失败")
    return results, running_instances


def step4_wait_and_check(running_instances, poll_interval=30, max_wait=1800):
    """步骤4: 动态监控任务状态（每30秒检查一次）- 修复版（增加失败次数限制）"""
    if not running_instances:
        log("\n  没有需要等待的任务")
        return [], []
    
    log("\n" + "="*70)
    log("【步骤4】动态监控任务状态")
    log("="*70)
    log(f"  共 {len(running_instances)} 个任务")
    log(f"  轮询间隔: {poll_interval}秒")
    log(f"  最大等待: {max_wait}秒 (30分钟)")
    
    start_time = time.time()
    completed_tasks = []
    failed_tasks = []
    pending = running_instances.copy()
    
    # 初始化失败计数
    for item in pending:
        item['fail_count'] = 0
    
    check_count = 0
    
    while pending and (time.time() - start_time) < max_wait:
        elapsed = int(time.time() - start_time)
        check_count += 1
        log(f"\n⏱️  第{check_count}次检查 (已等待 {elapsed}秒)")
        log("-" * 70)
        
        still_pending = []
        status_changed = False
        
        for item in pending:
            table = item['table']
            instance_id = item['instance_id']
            
            # 查询实例状态
            success, data, msg = ds_api_get(f"/projects/{PROJECT_CODE}/workflow-instances/{instance_id}")
            
            if success and data:
                state = data.get('state', 'UNKNOWN')
                
                if state in ['SUCCESS', 'FINISHED']:
                    log(f"  ✅ {table}: 完成 ({state})")
                    item['task']['final_status'] = 'success'
                    item['task']['end_time'] = data.get('endTime')
                    completed_tasks.append(item['task'])
                    status_changed = True
                elif state in ['FAILED', 'KILL', 'STOP']:
                    log(f"  ❌ {table}: 失败 ({state})")
                    item['task']['final_status'] = 'failed'
                    item['task']['error'] = f"状态: {state}"
                    failed_tasks.append(item['task'])
                    status_changed = True
                else:
                    # 仍在运行中，重置失败计数
                    item['fail_count'] = 0
                    log(f"  ⏳ {table}: {state}")
                    still_pending.append(item)
            else:
                # 查询失败，增加失败计数
                item['fail_count'] += 1
                if item['fail_count'] >= 3:
                    log(f"  ❌ {table}: 查询失败超过3次，标记为失败 ({msg})")
                    item['task']['final_status'] = 'failed'
                    item['task']['error'] = f"查询失败: {msg}"
                    failed_tasks.append(item['task'])
                    status_changed = True
                else:
                    log(f"  ⚠️  {table}: 查询失败 ({msg})，第{item['fail_count']}次")
                    still_pending.append(item)
        
        pending = still_pending
        
        # 显示汇总
        log("-" * 70)
        log(f"📊 当前状态: 成功={len(completed_tasks)}, 失败={len(failed_tasks)}, 运行中={len(pending)}")
        
        # 如果都完成了，立即退出
        if not pending:
            log(f"\n🎉 所有任务已完成！")
            break
        
        # 等待下一轮
        log(f"  还有 {len(pending)} 个任务运行中，{poll_interval}秒后再次检查...")
        time.sleep(poll_interval)
    
    # 处理超时任务
    if pending:
        log(f"\n⚠️  等待超时，以下任务未完成:")
        for item in pending:
            log(f"    - {item['table']}: {item['instance_id']}")
            item['task']['final_status'] = 'timeout'
            failed_tasks.append(item['task'])
    
    log(f"\n📊 最终结果:")
    log(f"  ✅ 成功: {len(completed_tasks)} 个")
    log(f"  ❌ 失败/超时: {len(failed_tasks)} 个")
    
    return completed_tasks, failed_tasks


def execute_repairs_in_batches(tasks, max_parallel=5):
    """分批执行修复任务，控制同时运行的实例数量"""
    if max_parallel <= 0:
        raise ValueError("max_parallel must be greater than 0")

    all_results = []
    all_completed_tasks = []
    all_failed_tasks = []

    total_batches = (len(tasks) + max_parallel - 1) // max_parallel

    for batch_index, start in enumerate(range(0, len(tasks), max_parallel), 1):
        batch_tasks = tasks[start:start + max_parallel]
        log("\n" + "=" * 70)
        log(f"【批次 {batch_index}/{total_batches}】执行 {len(batch_tasks)} 个修复任务")
        log("=" * 70)

        batch_results, running_instances = step3_start_repair(batch_tasks)
        completed_tasks, failed_tasks = step4_wait_and_check(running_instances)

        all_results.extend(batch_results)
        all_completed_tasks.extend(completed_tasks)
        all_failed_tasks.extend(failed_tasks)

    return all_results, all_completed_tasks, all_failed_tasks


def step5_execute_fuyan(completed_tasks, failed_tasks, alerts):
    """步骤5: 执行复验"""
    log("\n" + "="*70)
    log("【步骤5】执行复验")
    log("="*70)
    
    # 记录重跑次数
    log("\n5.1 记录重跑次数...")
    record_file = f"{WORKSPACE}/auto_repair_records/repair_counts.json"
    counts = {}
    if os.path.exists(record_file):
        with open(record_file, 'r') as f:
            counts = json.load(f)
    
    today = datetime.now().strftime('%Y-%m-%d')
    for task in completed_tasks:
        table = task['table']
        if table not in counts:
            counts[table] = {}
        counts[table][today] = counts[table].get(today, 0) + 1
        log(f"  📝 {table}: 今日第{counts[table][today]}次")
    
    with open(record_file, 'w') as f:
        json.dump(counts, f, indent=2)
    
    # 执行复验
    log(f"\n5.2 执行复验工作流...")
    fuyan_results = []
    
    for i, fuyan in enumerate(FUYAN_WORKFLOWS, 1):
        log(f"  [{i}] {fuyan['name']}")
        
        schedule_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'workflowDefinitionCode': fuyan['code'],
            'failureStrategy': 'CONTINUE',
            'warningType': 'NONE',
            'warningGroupId': 0,
            'execType': 'START_PROCESS',
            'environmentCode': 154818922491872,
            'tenantCode': 'dolphinscheduler',
            'dryRun': 0,
            'scheduleTime': schedule_time
        }
        
        success, result, msg = ds_api_post(f"/projects/{FUYAN_PROJECT_CODE}/executors/start-workflow-instance", data)
        if success:
            instance_id = result.get('data')
            if isinstance(instance_id, list) and len(instance_id) > 0:
                instance_id = instance_id[0]
            log(f"    ✅ 启动成功: {instance_id}")
            fuyan_results.append({'name': fuyan['name'], 'id': instance_id, 'status': 'success'})
        else:
            error_msg = result.get('msg', '未知错误')
            log(f"    ❌ 启动失败: {error_msg}")
            fuyan_results.append({'name': fuyan['name'], 'status': 'failed', 'error': error_msg})
    
    return fuyan_results


def step6_save_report(results, completed_tasks, failed_tasks, fuyan_results, alerts, manual_review_tasks=None):
    """步骤6: 保存记录并发送TV报告"""
    if manual_review_tasks is None:
        manual_review_tasks = []

    log("\n" + "="*70)
    log("【步骤6】保存记录")
    log("="*70)
    
    record_dir = f"{WORKSPACE}/auto_repair_records/{datetime.now().strftime('%Y-%m-%d')}"
    os.makedirs(record_dir, exist_ok=True)
    
    detail_file = f"{record_dir}/detail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(detail_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'manual_review_tasks': manual_review_tasks,
            'fuyan_results': fuyan_results,
        }, f, indent=2, ensure_ascii=False)
    
    log(f"  ✅ 记录已保存: {detail_file}")
    
    # 生成TV报告内容
    tv_report = generate_tv_report(completed_tasks, failed_tasks, fuyan_results, alerts, manual_review_tasks=manual_review_tasks)
    
    # 发送TV报告到钉钉
    send_tv_report_to_dingtalk(tv_report)


def generate_tv_report(completed_tasks, failed_tasks, fuyan_results, alerts, manual_review_tasks=None):
    """生成TV格式报告"""
    if manual_review_tasks is None:
        manual_review_tasks = []
    
    # 查询当前剩余未处理告警数量
    remaining_count = 0
    try:
        from alert.db_config import get_db_connection
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
                SELECT COUNT(*) as cnt
                FROM wattrel_quality_result
                WHERE result = 1 AND is_repaired = 0
                AND created_at >= DATE_SUB(NOW(), INTERVAL 3 DAY)
            """
            cursor.execute(sql)
            result = cursor.fetchone()
            remaining_count = result['cnt'] if result else 0
        conn.close()
    except Exception as e:
        log(f"  ⚠️ 查询剩余告警数量失败: {e}")
    
    report_lines = []
    report_lines.append("📺 【智能告警修复报告】")
    report_lines.append("")
    report_lines.append(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    # 扫描统计
    report_lines.append("📊 本次执行统计:")
    report_lines.append(f"  • 扫描告警: {len(alerts)} 个")
    report_lines.append(f"  • 修复成功: {len(completed_tasks)} 个")
    report_lines.append(f"  • 修复失败: {len(failed_tasks)} 个")
    report_lines.append(f"  • 人工处理: {len(manual_review_tasks)} 个")
    report_lines.append(f"  • 复验启动: {len(fuyan_results)} 个")
    report_lines.append("")
    
    # 剩余告警
    report_lines.append(f"📋 当前未处理告警: {remaining_count} 个")
    report_lines.append("")
    
    # 成功任务
    if completed_tasks:
        report_lines.append("✅ 【修复成功任务】")
        for task in completed_tasks:
            report_lines.append(f"  • {task['table']}")
            if task.get('end_time'):
                report_lines.append(f"    完成时间: {task['end_time']}")
        report_lines.append("")
    
    # 失败任务
    if failed_tasks:
        report_lines.append("❌ 【修复失败/超时任务】")
        for task in failed_tasks:
            error_msg = task.get('error', '未知错误')
            report_lines.append(f"  • {task['table']}")
            report_lines.append(f"    原因: {error_msg}")
        report_lines.append("")

    if manual_review_tasks:
        report_lines.append("⚠️ 【需人工处理】")
        for task in manual_review_tasks:
            report_lines.append(f"  • {task['table']}")
            report_lines.append(f"    原因: {task.get('error', '需人工处理')}")
        report_lines.append("")
    
    # 未找到工作流的任务
    not_found_tasks = [a for a in alerts if not any(t['table'] == a['table'] for t in completed_tasks + failed_tasks)]
    if not_found_tasks:
        report_lines.append("⚠️ 【未找到工作流(需人工处理)】")
        for task in not_found_tasks:
            report_lines.append(f"  • {task['table']}")
        report_lines.append("")
    
    # 复验工作流
    report_lines.append("🔄 【复验工作流状态】")
    for fuyan in fuyan_results:
        if fuyan.get('status') == 'success':
            report_lines.append(f"  ✅ {fuyan['name']}")
            if fuyan.get('id'):
                report_lines.append(f"     实例ID: {fuyan['id']}")
        else:
            report_lines.append(f"  ❌ {fuyan['name']}")
            if fuyan.get('error'):
                report_lines.append(f"     错误: {fuyan['error']}")
    report_lines.append("")
    
    # 结尾
    report_lines.append("=" * 40)
    report_lines.append("📌 智能告警修复系统自动生成")
    
    return "\n".join(report_lines)


def send_tv_report_to_dingtalk(report_content):
    """发送TV报告到钉钉群"""
    log("\n" + "="*70)
    log("【发送TV报告到钉钉群】")
    log("="*70)
    
    try:
        # 保存报告到文件
        report_file = f"{WORKSPACE}/auto_repair_records/{datetime.now().strftime('%Y-%m-%d')}/tv_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        log(f"✅ TV报告已生成: {report_file}")
        
        # 优先直接调用TV API，避免依赖本机 openclaw 命令
        try:
            from core.send_tv_report import send_tv_report

            mentions_env = os.environ.get('TV_MENTIONS', '').strip()
            mentions = [m.strip() for m in mentions_env.split(',') if m.strip()]
            result = send_tv_report(report_content, mentions=mentions)

            if result.get('success'):
                log(f"✅ TV报告已直接发送到TV API (HTTP {result.get('status_code')})")
            else:
                log(
                    "⚠️ 直接发送TV API失败: "
                    f"HTTP {result.get('status_code')}, {result.get('response')}"
                )
        except Exception as e:
            log(f"⚠️ 尝试直接发送TV API失败: {e}")
        
        # 兜底：控制台输出，便于n8n继续采集日志
        print(f"\n{'='*50}")
        print("📺 TV告警修复报告")
        print(f"{'='*50}")
        print(report_content)
        print(f"{'='*50}\n")
        
        log("✅ TV报告已输出到控制台")
        
    except Exception as e:
        log(f"❌ 发送TV报告时出错: {e}")
        import traceback
        traceback.print_exc()
    
    log("\n" + "="*70)


def main():
    """主函数"""
    log("="*70)
    log("🚀 智能告警修复流程（v5.2 最终修复版）")
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

    # 策略判断：疑似冗余数据告警首次允许重跑，后续转人工处理
    strategy_state = load_manual_review_state()
    runnable_tasks, manual_review_tasks = apply_repair_strategy(tasks, strategy_state)
    
    # 步骤3-4: 分批启动修复并动态监控（最多并行5个）
    results, completed_tasks, failed_tasks = execute_repairs_in_batches(runnable_tasks, max_parallel=5)

    record_redundant_retry_attempt(strategy_state, completed_tasks)
    record_manual_review_tasks(strategy_state, manual_review_tasks)
    save_manual_review_state(strategy_state)

    if manual_review_tasks:
        log("\n⚠️ 以下任务疑似冗余数据，已转人工处理，不再自动重跑:")
        for task in manual_review_tasks:
            log(f"  - {task['table']}: {task['error']}")

    results.extend(manual_review_tasks)
    
    # 步骤5: 执行复验
    fuyan_results = step5_execute_fuyan(completed_tasks, failed_tasks, alerts)
    
    # 步骤6: 保存记录并发送TV报告
    step6_save_report(results, completed_tasks, failed_tasks, fuyan_results, alerts, manual_review_tasks=manual_review_tasks)
    
    log("\n" + "="*70)
    log("✅ 流程完成")
    log("="*70)


if __name__ == '__main__':
    main()
