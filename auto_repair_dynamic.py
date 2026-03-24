#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能告警修复系统 - 完整动态搜索版

流程：
1. 用 search_table.py 逻辑搜索表在哪个工作流
2. 在工作流内找到处理该表的具体任务
3. 从告警SQL解析dt参数
4. 只执行那个任务

作者：OpenClaw
日期：2026-03-24
"""

import json
import subprocess
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

# ================= 配置区 =================
DB_CONFIG = {
    'host': '172.20.0.235',
    'port': 13306,
    'user': 'e_ds',
    'password': 'hAN0Hax1lop',
    'database': 'wattrel'
}

DS_CONFIG = {
    'base_url': 'http://172.20.0.235:12345/dolphinscheduler',
    'token': '0cad23ded0f0e942381fc9717c1581a8',
    'project_code': '158514956085248'
}

DINGTALK_CONVERSATION_ID = 'cidune9y06rl1j0uelxqielqw=='
DAYS_LIMIT = 10
MAX_PARALLEL = 2
# ==========================================


class Logger:
    """日志记录器"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = f"/home/node/.openclaw/workspace/auto_repair_logs/{datetime.now().strftime('%Y-%m-%d')}"
        os.makedirs(self.log_dir, exist_ok=True)
        self.main_log = f"{self.log_dir}/repair_main_{self.timestamp}.log"
        
    def log(self, message, level='INFO'):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [{level}] {message}"
        
        with open(self.main_log, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
        print(log_line)
        
        # 实时发送到钉钉
        self._send_to_dingtalk(message)
    
    def _send_to_dingtalk(self, message):
        try:
            cmd = [
                'openclaw', 'message', 'send',
                '--channel', 'dingtalk-connector',
                '--target', f'group:{DINGTALK_CONVERSATION_ID}',
                '--message', message
            ]
            subprocess.run(cmd, capture_output=True, timeout=10)
        except:
            pass


class DynamicSearchRepair:
    """动态搜索修复系统"""
    
    def __init__(self):
        self.logger = Logger()
    
    def get_all_workflows(self):
        """获取所有工作流列表"""
        try:
            curl_cmd = f"""curl -s "{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/process-definition?pageNo=1&pageSize=100" \
  -H "token: {DS_CONFIG['token']}"""
            
            result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                if response.get('code') == 0:
                    return response.get('data', {}).get('totalList', [])
            return []
        except Exception as e:
            self.logger.log(f"获取工作流列表失败: {e}", 'ERROR')
            return []
    
    def search_table_in_workflow(self, workflow_code, table_name):
        """在工作流中搜索表"""
        try:
            # 获取工作流详情
            curl_cmd = f"""curl -s "{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/process-definition/{workflow_code}" \
  -H "token: {DS_CONFIG['token']}"""
            
            result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                if response.get('code') == 0:
                    data = response.get('data', {})
                    wf_name = data.get('name', '')
                    tasks = data.get('taskDefinitionList', [])
                    
                    # 在每个任务中搜索表名
                    for task in tasks:
                        task_name = task.get('name', '')
                        task_code = task.get('code')
                        task_params = task.get('taskParams', '{}')
                        
                        # 解析SQL
                        if isinstance(task_params, str):
                            try:
                                task_params = json.loads(task_params)
                            except:
                                task_params = {}
                        
                        raw_script = task_params.get('rawScript', '') if isinstance(task_params, dict) else ''
                        
                        # 检查SQL或任务名是否包含表名
                        if table_name.lower() in raw_script.lower():
                            return {
                                'found': True,
                                'workflow_name': wf_name,
                                'workflow_code': workflow_code,
                                'task_name': task_name,
                                'task_code': task_code,
                                'match_type': 'SQL包含表名'
                            }
                        
                        # 检查任务名
                        table_parts = table_name.split('_')
                        if len(table_parts) >= 3:
                            key_part = '_'.join(table_parts[2:])  # account_repay
                            if key_part.lower() in task_name.lower():
                                return {
                                    'found': True,
                                    'workflow_name': wf_name,
                                    'workflow_code': workflow_code,
                                    'task_name': task_name,
                                    'task_code': task_code,
                                    'match_type': f'任务名包含{key_part}'
                                }
            
            return {'found': False}
        except Exception as e:
            self.logger.log(f"搜索失败: {e}", 'ERROR')
            return {'found': False}
    
    def find_workflow_for_table(self, table_name):
        """动态搜索表在哪个工作流中"""
        self.logger.log(f"🔍 动态搜索表 {table_name} 所在工作流...")
        
        # 获取所有工作流
        workflows = self.get_all_workflows()
        self.logger.log(f"共有 {len(workflows)} 个工作流需要搜索")
        
        for wf in workflows:
            wf_code = wf.get('code')
            wf_name = wf.get('name', '')
            
            # 在每个工作流中搜索
            result = self.search_table_in_workflow(wf_code, table_name)
            
            if result.get('found'):
                self.logger.log(f"✅ 找到！工作流: {result['workflow_name']}, 任务: {result['task_name']}")
                return result
        
        self.logger.log(f"❌ 在所有工作流中都未找到 {table_name}", 'WARN')
        return None
    
    def extract_dt_from_alert(self, alert_content):
        """从告警内容解析dt参数"""
        # 从SQL中提取日期
        # 匹配: '2026-03-22 00:00:00' 或 '2026-03-22'
        matches = re.findall(r'(\d{4}-\d{2}-\d{2})', alert_content)
        
        if matches:
            dt = matches[0]
            self.logger.log(f"📅 从告警解析到dt: {dt}")
            return dt
        
        self.logger.log("⚠️ 无法从告警解析dt", 'WARN')
        return None
    
    def validate_dt(self, dt_str):
        """验证dt是否合法"""
        try:
            dt = datetime.strptime(dt_str, '%Y-%m-%d')
            today = datetime.now()
            diff_days = (today - dt).days
            
            if diff_days > DAYS_LIMIT:
                self.logger.log(f"dt={dt_str} 超过{DAYS_LIMIT}天限制", 'WARN')
                return False
            if diff_days < 0:
                self.logger.log(f"dt={dt_str} 是未来日期", 'WARN')
                return False
            
            return True
        except:
            self.logger.log(f"dt格式错误: {dt_str}", 'ERROR')
            return False
    
    def start_single_task(self, workflow_code, task_code, task_name, table_name, dt):
        """只启动特定任务"""
        self.logger.log(f"🚀 启动任务: {task_name} (表: {table_name}, dt: {dt})")
        
        curl_cmd = f"""curl -s -X POST "{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/executors/start-process-instance" \
  -H "token: {DS_CONFIG['token']}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "processDefinitionCode={workflow_code}" \
  -d "startNodeList={task_code}" \
  -d "taskDependType=TASK_ONLY" \
  -d "failureStrategy=CONTINUE" \
  -d "warningType=NONE" \
  -d "execType=START_PROCESS" \
  -d "startParams={{\\"dt\\":\\"{dt}\\"}}" \
  --connect-timeout 30"""
        
        try:
            result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True, timeout=35)
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                if response.get('code') == 0:
                    instance_id = response.get('data')
                    self.logger.log(f"✅ 启动成功！实例ID: {instance_id}")
                    return True
                else:
                    self.logger.log(f"❌ 启动失败: {response.get('msg')}", 'ERROR')
                    return False
            else:
                self.logger.log(f"❌ curl失败: {result.stderr}", 'ERROR')
                return False
        except Exception as e:
            self.logger.log(f"❌ 异常: {e}", 'ERROR')
            return False
    
    def repair_alert(self, alert):
        """修复单个告警"""
        alert_id = alert.get('id')
        content = alert.get('content', '')
        
        self.logger.log(f"\n{'='*60}")
        self.logger.log(f"处理告警 ID: {alert_id}")
        self.logger.log(f"{'='*60}")
        
        # 步骤1: 提取表名
        matches = re.findall(r'(dwd_\w+|dwb_\w+|ods_\w+|ads_\w+)', content)
        if not matches:
            self.logger.log("未找到表名", 'WARN')
            return False
        
        table_name = matches[0]
        self.logger.log(f"📋 表名: {table_name}")
        
        # 步骤2: 解析dt
        dt = self.extract_dt_from_alert(content)
        if not dt or not self.validate_dt(dt):
            return False
        
        # 步骤3: 动态搜索工作流和任务
        search_result = self.find_workflow_for_table(table_name)
        if not search_result:
            return False
        
        # 步骤4: 只启动那个特定任务
        return self.start_single_task(
            search_result['workflow_code'],
            search_result['task_code'],
            search_result['task_name'],
            table_name,
            dt
        )
    
    def run(self):
        """运行完整修复流程"""
        self.logger.log("="*80)
        self.logger.log("🚀 智能告警修复系统（动态搜索版）")
        self.logger.log("="*80)
        
        # 查询告警
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_start = f"{yesterday} 00:00:00"
        
        js_code = f"""
const mysql = require('/tmp/node_modules/mysql2/promise');
async function query() {{
    const conn = await mysql.createConnection({{
        host: '{DB_CONFIG['host']}', port: {DB_CONFIG['port']}, user: '{DB_CONFIG['user']}',
        password: '{DB_CONFIG['password']}', database: '{DB_CONFIG['database']}', charset: 'utf8mb4'
    }});
    const [rows] = await conn.execute(`
        SELECT id, content, type, created_at
        FROM wattrel_quality_alert
        WHERE created_at >= ?
          AND status = 0
          AND content NOT LIKE '%已恢复%'
        ORDER BY created_at DESC
    `, ['{yesterday_start}']);
    await conn.end();
    console.log(JSON.stringify(rows));
}}
query().catch(e => console.error(e));
"""
        
        try:
            result = subprocess.run(['node', '-e', js_code], capture_output=True, text=True, timeout=15)
            alerts = json.loads(result.stdout) if result.returncode == 0 else []
            
            self.logger.log(f"\n📊 发现 {len(alerts)} 条告警")
            
            if not alerts:
                self.logger.log("✅ 没有需要修复的告警")
                return
            
            # 逐个修复
            success_count = 0
            for alert in alerts:
                if self.repair_alert(alert):
                    success_count += 1
            
            self.logger.log(f"\n{'='*80}")
            self.logger.log(f"✅ 修复完成: 成功 {success_count}/{len(alerts)}")
            self.logger.log(f"{'='*80}")
            
        except Exception as e:
            self.logger.log(f"系统异常: {e}", 'ERROR')


if __name__ == "__main__":
    system = DynamicSearchRepair()
    system.run()
