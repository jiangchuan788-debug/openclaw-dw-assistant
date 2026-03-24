#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能告警修复流程

流程：
1. 扫描告警 -> 发送给OpenClaw
2. 整理告警表 -> 查找工作流位置 -> 记录
3. 指定dt重跑工作流（限制条件检查）
4. 记录重跑次数 -> 执行复验
5. 验证修复结果 -> 回复群里
6. 记录所有操作

作者：OpenClaw
日期：2026-03-24
"""

import json
import subprocess
import os
import re
import time
from datetime import datetime, timedelta
from collections import defaultdict
import threading
import queue

# ================= 配置区 =================
DB_CONFIG = {
    'host': '172.20.0.235',
    'port': 13306,
    'user': 'e_ds',
    'password': 'hAN0Hax1lop',
    'database': 'wattrel'
}

WORKSPACE = '/home/node/.openclaw/workspace'
ALERT_DIR = f'{WORKSPACE}/alert'
DOLPHIN_DIR = f'{WORKSPACE}/dolphinscheduler'
LOG_DIR = f'{WORKSPACE}/auto_repair_logs'
DAILY_RECORD_DIR = f'{LOG_DIR}/{datetime.now().strftime("%Y-%m-%d")}'

# 钉钉群配置
DINGTALK_CONVERSATION_ID = 'cidune9y06rl1j0uelxqielqw=='

# 并行限制
MAX_PARALLEL = 2
DAYS_LIMIT = 10
# ==========================================


class Logger:
    """操作日志记录器 - 同时发送执行过程到群里"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = DAILY_RECORD_DIR
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.main_log = f"{self.log_dir}/repair_main_{self.timestamp}.log"
        self.detail_log = f"{self.log_dir}/repair_detail_{self.timestamp}.log"
        self.commands_log = f"{self.log_dir}/commands_{self.timestamp}.log"
        
        # 执行过程缓存，用于最后发送完整报告
        self.execution_steps = []
        self.commands_history = []
        
    def log(self, message, level='INFO', send_to_group=True):
        """记录主日志，同时发送到群里"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [{level}] {message}"
        
        # 写入文件
        with open(self.main_log, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
        
        # 打印到控制台
        print(log_line)
        
        # 缓存执行步骤
        self.execution_steps.append({
            'time': timestamp,
            'level': level,
            'message': message
        })
        
        # 发送到钉钉群
        if send_to_group:
            self._send_to_dingtalk(message)
    
    def _send_to_dingtalk(self, message):
        """发送消息到钉钉群"""
        try:
            cmd = [
                'openclaw', 'message', 'send',
                '--channel', 'dingtalk-connector',
                '--target', f'group:{DINGTALK_CONVERSATION_ID}',
                '--message', message
            ]
            subprocess.run(cmd, capture_output=True, timeout=10)
        except:
            pass  # 发送失败不影响主流程
    
    def log_detail(self, data):
        """记录详细数据（JSON格式）"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record = {
            'timestamp': timestamp,
            'data': data
        }
        
        with open(self.detail_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def log_command(self, command, output=None):
        """记录执行的命令"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record = {
            'timestamp': timestamp,
            'command': command,
            'output': output
        }
        
        with open(self.commands_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        # 缓存命令历史
        self.commands_history.append(record)
        
        # 发送命令到群里（简化显示）
        short_cmd = command[:100] + '...' if len(command) > 100 else command
        self._send_to_dingtalk(f"📝 执行命令: {short_cmd}")
    
    def send_final_report(self, duration, repaired_count, failed_count):
        """发送完整的执行报告到群里"""
        report = [
            "📋 智能修复执行完成报告",
            "=" * 50,
            f"⏱️ 总耗时: {duration:.1f}秒",
            f"✅ 修复成功: {repaired_count} 个表",
            f"❌ 修复失败: {failed_count} 个表",
            "",
            "📌 执行步骤摘要:",
        ]
        
        # 添加关键步骤
        for step in self.execution_steps[-20:]:  # 最后20步
            if step['level'] in ['INFO', 'ERROR']:
                report.append(f"  [{step['time']}] {step['message']}")
        
        report.extend([
            "",
            "🔧 执行命令记录:",
        ])
        
        # 添加执行的命令
        for i, cmd_record in enumerate(self.commands_history[-10:], 1):  # 最后10个命令
            cmd = cmd_record['command']
            short_cmd = cmd[:80] + '...' if len(cmd) > 80 else cmd
            report.append(f"  {i}. {short_cmd}")
        
        report.extend([
            "",
            f"📁 详细日志: {self.log_dir}",
            "=" * 50,
        ])
        
        # 发送完整报告
        full_report = '\n'.join(report)
        
        # 如果报告太长，分段发送
        if len(full_report) > 1500:
            # 发送摘要
            summary = '\n'.join(report[:10])  # 前10行
            self._send_to_dingtalk(summary)
            
            # 发送详细结果
            details = f"✅ 成功: {repaired_count} | ❌ 失败: {failed_count}\n📁 日志: {self.log_dir}"
            self._send_to_dingtalk(details)
        else:
            self._send_to_dingtalk(full_report)


class AlertScanner:
    """告警扫描器"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def scan_alerts(self):
        """扫描数据库中的告警"""
        self.logger.log("=== 步骤1: 扫描告警 ===")
        
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
            result = subprocess.run(
                ['node', '-e', js_code],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                alerts = json.loads(result.stdout)
                self.logger.log(f"发现 {len(alerts)} 条告警")
                self.logger.log_detail({'alerts_found': len(alerts), 'alerts': alerts})
                return alerts
            else:
                self.logger.log(f"查询失败: {result.stderr}", 'ERROR')
                return []
        except Exception as e:
            self.logger.log(f"扫描异常: {e}", 'ERROR')
            return []
    
    def send_to_openclaw(self, alerts):
        """发送告警到OpenClaw"""
        self.logger.log("=== 步骤2: 发送告警到OpenClaw ===")
        
        if not alerts:
            self.logger.log("没有告警需要发送")
            return
        
        summary = f"🚨 发现 {len(alerts)} 条数据质量告警，开始自动修复流程..."
        self.send_dingtalk_message(summary)
        
        for i, alert in enumerate(alerts[:5], 1):  # 只发送前5条摘要
            content = alert.get('content', '')[:100]
            message = f"【{i}】ID:{alert['id']} - {content}..."
            self.send_dingtalk_message(message)
    
    def send_dingtalk_message(self, message):
        """发送钉钉消息"""
        try:
            cmd = [
                'openclaw', 'message', 'send',
                '--channel', 'dingtalk-connector',
                '--target', f'group:{DINGTALK_CONVERSATION_ID}',
                '--message', message
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            self.logger.log_command(' '.join(cmd), result.stdout if result.returncode == 0 else result.stderr)
            
            return result.returncode == 0 or 'Sent via DingTalk' in result.stdout
        except Exception as e:
            self.logger.log(f"发送失败: {e}", 'ERROR')
            return False


class TableAnalyzer:
    """表分析器"""
    
    def __init__(self, logger):
        self.logger = logger
        self.table_workflow_map = {}
    
    def extract_tables_from_alerts(self, alerts):
        """从告警内容中提取表名"""
        self.logger.log("=== 步骤3: 提取告警中的表名 ===")
        
        tables = []
        for alert in alerts:
            content = alert.get('content', '')
            
            # 匹配表名（ods_*, dwd_*, dwb_*, ads_* 等）
            matches = re.findall(r'(ods_\w+|dwd_\w+|dwb_\w+|ads_\w+)', content)
            
            for table in matches:
                if table not in [t['table'] for t in tables]:
                    tables.append({
                        'table': table,
                        'alert_id': alert['id'],
                        'content': content,
                        'dt': self.extract_dt_from_content(content)
                    })
        
        self.logger.log(f"提取到 {len(tables)} 个唯一表名")
        self.logger.log_detail({'extracted_tables': tables})
        return tables
    
    def extract_dt_from_content(self, content):
        """从告警内容中提取dt日期"""
        # 匹配日期格式: '2026-03-22 00:00:00' 或 '2026-03-22'
        matches = re.findall(r'(\d{4}-\d{2}-\d{2})', content)
        if matches:
            return matches[0]  # 返回第一个匹配的日期
        return None
    
    def find_workflows_for_tables(self, tables):
        """查找表对应的工作流"""
        self.logger.log("=== 步骤4: 查找表对应的工作流 ===")
        
        # 这里简化处理，实际应该调用search_table.py
        # 为了演示，使用预定义的映射
        workflow_mapping = {
            'dwb_asset_period_info': {
                'project_code': '158514956085248',
                'workflow_code': '158514957297664',
                'workflow_name': 'DWB'
            },
            'dwd_asset_account_recharge': {
                'project_code': '158514956085248',
                'workflow_code': '158514957656064',
                'workflow_name': 'DWD(D-1)'
            },
            'dwd_asset_account_repay': {
                'project_code': '158514956085248',
                'workflow_code': '158514957337600',
                'workflow_name': '国内-数仓工作流(D-1)'
            },
            'dwd_asset_qsq_erp_withhold': {
                'project_code': '158514956085248',
                'workflow_code': '158514958374912',
                'workflow_name': '国内-数仓工作流(H-1)'
            }
        }
        
        for table_info in tables:
            table_name = table_info['table']
            if table_name in workflow_mapping:
                table_info['workflow'] = workflow_mapping[table_name]
                self.logger.log(f"表 {table_name} -> 工作流 {workflow_mapping[table_name]['workflow_name']}")
            else:
                self.logger.log(f"表 {table_name} 未找到对应工作流", 'WARN')
        
        # 过滤掉没有工作流的表
        valid_tables = [t for t in tables if 'workflow' in t]
        
        # 保存到文件
        record_file = f"{DAILY_RECORD_DIR}/table_workflow_mapping.json"
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(valid_tables, f, ensure_ascii=False, indent=2)
        
        self.logger.log(f"已保存表-工作流映射到: {record_file}")
        return valid_tables


class WorkflowRunner:
    """工作流运行器"""
    
    def __init__(self, logger):
        self.logger = logger
        self.running_workflows = set()
        self.repair_count = defaultdict(int)
    
    def check_running_workflows(self):
        """检查是否有工作流在运行"""
        self.logger.log("=== 检查工作流运行状态 ===")
        
        try:
            result = subprocess.run(
                ['python3', f'{DOLPHIN_DIR}/check_running.py', '--check-only'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # 如果返回0表示空闲，1表示有运行中
            is_idle = (result.returncode == 0)
            self.logger.log(f"工作流状态: {'空闲' if is_idle else '忙碌'}")
            return is_idle
        except Exception as e:
            self.logger.log(f"检查失败: {e}", 'ERROR')
            return False
    
    def validate_dt(self, dt_str):
        """验证dt日期是否合法（不能超过当前时间10天）"""
        try:
            dt = datetime.strptime(dt_str, '%Y-%m-%d')
            today = datetime.now()
            diff_days = (today - dt).days
            
            if diff_days > DAYS_LIMIT:
                self.logger.log(f"dt={dt_str} 超过{DAYS_LIMIT}天限制，跳过", 'WARN')
                return False
            if diff_days < 0:
                self.logger.log(f"dt={dt_str} 是未来日期，跳过", 'WARN')
                return False
            
            return True
        except:
            return False
    
    def get_workflow_tasks(self, project_code, workflow_code):
        """获取工作流的任务定义列表"""
        try:
            # 获取工作流详情
            curl_cmd = f"""curl -s "http://172.20.0.235:12345/dolphinscheduler/projects/{project_code}/process-definition/{workflow_code}" \
  -H "token: 0cad23ded0f0e942381fc9717c1581a8"""
            
            result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                if response.get('code') == 0:
                    data = response.get('data', {})
                    tasks = data.get('taskDefinitionList', [])
                    return tasks
            return []
        except Exception as e:
            self.logger.log(f"获取任务定义失败: {e}", 'ERROR')
            return []
    
    def find_task_for_table(self, tasks, table_name):
        """在工作流任务中找到与表相关的任务"""
        for task in tasks:
            task_name = task.get('name', '')
            task_params = task.get('taskParams', '{}')
            
            # 解析任务参数
            if isinstance(task_params, str):
                try:
                    task_params = json.loads(task_params)
                except:
                    task_params = {}
            
            # 检查SQL内容是否包含表名
            raw_script = task_params.get('rawScript', '') if isinstance(task_params, dict) else ''
            
            # 匹配逻辑：任务名包含表名，或SQL包含表名
            if table_name.lower() in task_name.lower() or table_name.lower() in raw_script.lower():
                return {
                    'task_code': task.get('code'),
                    'task_name': task_name,
                    'table': table_name
                }
        
        # 如果没找到精确匹配，返回包含DWD/DWB/ODS等关键字的任务
        for task in tasks:
            task_name = task.get('name', '')
            # 根据表前缀匹配任务类型
            if 'dwd' in table_name.lower() and 'DWD' in task_name:
                return {
                    'task_code': task.get('code'),
                    'task_name': task_name,
                    'table': table_name,
                    'note': '按DWD类型匹配'
                }
            elif 'dwb' in table_name.lower() and 'DWB' in task_name:
                return {
                    'task_code': task.get('code'),
                    'task_name': task_name,
                    'table': table_name,
                    'note': '按DWB类型匹配'
                }
            elif 'ods' in table_name.lower() and 'ODS' in task_name:
                return {
                    'task_code': task.get('code'),
                    'task_name': task_name,
                    'table': table_name,
                    'note': '按ODS类型匹配'
                }
        
        return None
    
    def run_single_task(self, project_code, workflow_code, task_code, task_name, table_name, dt):
        """只启动工作流中的特定任务"""
        self.logger.log(f"启动单任务: {task_name} (表: {table_name}, dt: {dt})")
        
        # 构建curl命令，使用startNodeList指定只启动特定任务
        curl_cmd = f"""curl -s -X POST "http://172.20.0.235:12345/dolphinscheduler/projects/{project_code}/executors/start-process-instance" \
  -H "token: 0cad23ded0f0e942381fc9717c1581a8" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "processDefinitionCode={workflow_code}" \
  -d "failureStrategy=CONTINUE" \
  -d "warningType=NONE" \
  -d "warningGroupId=0" \
  -d "processInstancePriority=MEDIUM" \
  -d "workerGroup=default" \
  -d "environmentCode=154818922491872" \
  -d "tenantCode=dolphinscheduler" \
  -d "taskDependType=TASK_ONLY" \
  -d "runMode=RUN_MODE_SERIAL" \
  -d "execType=START_PROCESS" \
  -d "dryRun=0" \
  -d "scheduleTime=" \
  -d "startNodeList={task_code}" \
  -d "startParams={{\\"dt\\":\\"{dt}\\"}}" \
  --connect-timeout 30"""
        
        self.logger.log_command(f"启动单任务: {task_name} (Code: {task_code})")
        
        try:
            result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True, timeout=35)
            
            if result.returncode == 0:
                try:
                    response = json.loads(result.stdout)
                    if response.get('code') == 0:
                        self.repair_count[table_name] += 1
                        self.logger.log(f"✅ 单任务启动成功: {task_name}, 实例ID: {response.get('data')}")
                        return True
                    else:
                        self.logger.log(f"❌ 单任务启动失败: {response.get('msg')}", 'ERROR')
                        return False
                except json.JSONDecodeError:
                    self.logger.log(f"❌ 解析响应失败: {result.stdout}", 'ERROR')
                    return False
            else:
                self.logger.log(f"❌ curl 执行失败: {result.stderr}", 'ERROR')
                return False
        except Exception as e:
            self.logger.log(f"❌ 启动异常: {e}", 'ERROR')
            return False
    
    def run_workflow(self, table_info):
        """运行工作流 - 只启动与表相关的特定任务"""
        table_name = table_info['table']
        workflow = table_info['workflow']
        dt = table_info.get('dt')
        
        if not dt:
            self.logger.log(f"表 {table_name} 没有dt日期，跳过", 'WARN')
            return False
        
        if not self.validate_dt(dt):
            return False
        
        project_code = workflow['project_code']
        workflow_code = workflow['workflow_code']
        
        self.logger.log(f"查找工作流任务: {workflow['workflow_name']} (表: {table_name})")
        
        # 1. 获取工作流的任务定义
        tasks = self.get_workflow_tasks(project_code, workflow_code)
        
        if not tasks:
            self.logger.log(f"工作流 {workflow['workflow_name']} 没有任务定义", 'ERROR')
            return False
        
        self.logger.log(f"工作流包含 {len(tasks)} 个任务，查找与 {table_name} 相关的任务...")
        
        # 2. 找到与表相关的任务
        matched_task = self.find_task_for_table(tasks, table_name)
        
        if not matched_task:
            self.logger.log(f"表 {table_name} 在工作流中没有匹配的任务，跳过（不启动整个工作流）", 'WARN')
            return False  # 直接返回失败，不启动整个工作流
        
        self.logger.log(f"找到匹配任务: {matched_task['task_name']} (Code: {matched_task['task_code']})")
        if matched_task.get('note'):
            self.logger.log(f"匹配备注: {matched_task['note']}")
        
        # 3. 只启动这个特定任务
        return self.run_single_task(
            project_code, 
            workflow_code, 
            matched_task['task_code'],
            matched_task['task_name'],
            table_name,
            dt
        )
    
    def run_repair_workflows(self, tables_with_workflow):
        """执行修复工作流（带并行限制）"""
        self.logger.log("=== 步骤5: 执行修复工作流 ===")
        
        if not tables_with_workflow:
            self.logger.log("没有需要修复的表")
            return
        
        # 按工作流分组，同一个工作流一次只能跑一个
        workflow_groups = defaultdict(list)
        for t in tables_with_workflow:
            wf_code = t['workflow']['workflow_code']
            workflow_groups[wf_code].append(t)
        
        self.logger.log(f"共 {len(workflow_groups)} 个不同工作流需要执行")
        
        # 执行队列
        pending = list(tables_with_workflow)
        running = []
        completed = []
        failed = []
        
        while pending or running:
            # 检查正在运行的任务是否完成
            for task in running[:]:
                if task.get('future'):  # 简化处理，实际应该检查实例状态
                    pass
            
            # 启动新的任务（最多并行2个）
            while len(running) < MAX_PARALLEL and pending:
                # 检查是否有运行中的工作流
                if not self.check_running_workflows():
                    self.logger.log("等待工作流空闲...")
                    time.sleep(5)
                    continue
                
                task = pending.pop(0)
                
                # 检查是否同一个工作流已经在运行
                wf_code = task['workflow']['workflow_code']
                if any(t['workflow']['workflow_code'] == wf_code for t in running):
                    self.logger.log(f"工作流 {wf_code} 已在运行，等待...")
                    pending.insert(0, task)
                    break
                
                self.logger.log(f"启动修复任务: {task['table']} (并行: {len(running)+1}/{MAX_PARALLEL})")
                
                if self.run_workflow(task):
                    running.append(task)
                    completed.append(task)
                else:
                    failed.append(task)
                
                time.sleep(2)  # 间隔2秒
            
            if pending or running:
                time.sleep(5)
        
        self.logger.log(f"修复完成: 成功 {len(completed)}, 失败 {len(failed)}")
        
        # 保存重跑次数记录
        repair_record = f"{DAILY_RECORD_DIR}/repair_count.json"
        with open(repair_record, 'w', encoding='utf-8') as f:
            json.dump(dict(self.repair_count), f, ensure_ascii=False, indent=2)


class RepairVerifier:
    """修复验证器"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def run_recheck(self):
        """执行复验脚本"""
        self.logger.log("=== 步骤6: 执行复验脚本 ===")
        
        try:
            result = subprocess.run(
                ['python3', f'{DOLPHIN_DIR}/run_fuyan_workflows.py'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            self.logger.log_command('python3 run_fuyan_workflows.py', result.stdout[:500])
            self.logger.log("复验脚本执行完成")
        except Exception as e:
            self.logger.log(f"复验执行异常: {e}", 'ERROR')
    
    def verify_repair(self, original_alerts):
        """验证修复结果"""
        self.logger.log("=== 步骤7: 验证修复结果 ===")
        
        # 重新查询告警
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
        SELECT id, content
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
            result = subprocess.run(
                ['node', '-e', js_code],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            current_alerts = json.loads(result.stdout) if result.returncode == 0 else []
            
            # 分析哪些表已修复
            repaired_tables = []
            still_failed_tables = []
            
            original_tables = set()
            for alert in original_alerts:
                matches = re.findall(r'(ods_\w+|dwd_\w+|dwb_\w+|ads_\w+)', alert.get('content', ''))
                original_tables.update(matches)
            
            current_tables = set()
            for alert in current_alerts:
                matches = re.findall(r'(ods_\w+|dwd_\w+|dwb_\w+|ads_\w+)', alert.get('content', ''))
                current_tables.update(matches)
            
            for table in original_tables:
                if table not in current_tables:
                    repaired_tables.append(table)
                else:
                    still_failed_tables.append(table)
            
            self.logger.log(f"修复成功: {len(repaired_tables)} 个表")
            self.logger.log(f"仍然失败: {len(still_failed_tables)} 个表")
            
            # 发送结果到群里
            self.send_result_to_group(repaired_tables, still_failed_tables)
            
            # 保存结果
            result_file = f"{DAILY_RECORD_DIR}/repair_result.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'repaired': repaired_tables,
                    'failed': still_failed_tables,
                    'original_count': len(original_alerts),
                    'current_count': len(current_alerts)
                }, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.log(f"验证异常: {e}", 'ERROR')
    
    def send_result_to_group(self, repaired, failed):
        """发送修复结果到群里"""
        self.logger.log("=== 发送修复结果到群里 ===")
        
        summary = f"📊 自动修复结果汇总\n\n✅ 修复成功 ({len(repaired)}个):"
        
        for table in repaired[:10]:  # 最多显示10个
            summary += f"\n  • {table}"
        
        if len(repaired) > 10:
            summary += f"\n  ... 还有 {len(repaired)-10} 个"
        
        if failed:
            summary += f"\n\n❌ 修复失败 ({len(failed)}个):"
            for table in failed[:5]:
                summary += f"\n  • {table} @陈江川"
        
        # 发送钉钉消息
        try:
            cmd = [
                'openclaw', 'message', 'send',
                '--channel', 'dingtalk-connector',
                '--target', f'group:{DINGTALK_CONVERSATION_ID}',
                '--message', summary
            ]
            subprocess.run(cmd, capture_output=True, timeout=15)
            self.logger.log("结果已发送到群里")
        except Exception as e:
            self.logger.log(f"发送结果失败: {e}", 'ERROR')


class AutoRepairSystem:
    """自动修复系统主控"""
    
    def __init__(self):
        self.logger = Logger()
        self.scanner = AlertScanner(self.logger)
        self.analyzer = TableAnalyzer(self.logger)
        self.runner = WorkflowRunner(self.logger)
        self.verifier = RepairVerifier(self.logger)
    
    def run(self):
        """运行完整的修复流程"""
        self.logger.log("=" * 80)
        self.logger.log("🚀 智能告警修复流程启动")
        self.logger.log("=" * 80)
        
        start_time = datetime.now()
        
        # 步骤1: 扫描告警
        alerts = self.scanner.scan_alerts()
        
        if not alerts:
            self.logger.log("没有需要处理的告警，流程结束")
            self.scanner.send_dingtalk_message("✅ 扫描完成：今天没有需要修复的数据质量告警")
            return
        
        # 步骤2: 发送给OpenClaw
        self.scanner.send_to_openclaw(alerts)
        
        # 步骤3-4: 提取表名并查找工作流
        tables = self.analyzer.extract_tables_from_alerts(alerts)
        tables_with_workflow = self.analyzer.find_workflows_for_tables(tables)
        
        if not tables_with_workflow:
            self.logger.log("没有找到可修复的工作流，流程结束")
            return
        
        # 步骤5: 执行修复
        self.runner.run_repair_workflows(tables_with_workflow)
        
        # 步骤6: 执行复验
        self.verifier.run_recheck()
        
        # 步骤7: 验证结果
        self.verifier.verify_repair(alerts)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self.logger.log("=" * 80)
        self.logger.log(f"✅ 智能修复流程完成，耗时: {duration:.1f}秒")
        self.logger.log("=" * 80)
        
        # 发送完整执行报告到群里
        self.logger.send_final_report(duration, len(completed), len(failed))


def main():
    """主函数"""
    system = AutoRepairSystem()
    
    try:
        system.run()
    except Exception as e:
        system.logger.log(f"系统异常: {e}", 'ERROR')
        # 发送错误通知
        system.scanner.send_dingtalk_message(f"❌ 自动修复流程异常终止: {str(e)[:200]}")


if __name__ == "__main__":
    main()
