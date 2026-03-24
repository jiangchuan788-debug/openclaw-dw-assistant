#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能告警修复系统 - 精确到表级别任务

逻辑：
1. 根据表名推断类型（DWD/DWB/ODS）
2. 找到对应类型的工作流
3. 在工作流内搜索包含表名的具体任务
4. 只执行那个任务（带dt参数）

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
    'project_code': '158514956085248'  # 国内数仓-工作流项目
}

DINGTALK_CONVERSATION_ID = 'cidune9y06rl1j0uelxqielqw=='
DAYS_LIMIT = 10
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


class SmartRepairSystem:
    """智能修复系统"""
    
    def __init__(self):
        self.logger = Logger()
    
    def infer_workflow_type(self, table_name):
        """根据表名推断工作流类型"""
        if table_name.startswith('dwd_'):
            return 'DWD'
        elif table_name.startswith('dwb_'):
            return 'DWB'
        elif table_name.startswith('ods_'):
            return 'ODS'
        elif table_name.startswith('ads_'):
            return 'ADS'
        else:
            return None
    
    def get_workflows_by_type(self, workflow_type):
        """获取指定类型的工作流列表"""
        try:
            # 查询项目下所有工作流
            curl_cmd = f"""curl -s "{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/process-definition?pageNo=1&pageSize=100" \
  -H "token: {DS_CONFIG['token']}"""
            
            result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                if response.get('code') == 0:
                    workflows = response.get('data', {}).get('totalList', [])
                    
                    # 筛选包含类型关键字的工作流（更宽松的匹配）
                    matched = []
                    for wf in workflows:
                        wf_name = wf.get('name', '')
                        # 匹配 DWD、DWD(D-1)、DWD-xxx 等格式
                        if workflow_type in wf_name or workflow_type.lower() in wf_name.lower():
                            matched.append({
                                'code': wf.get('code'),
                                'name': wf_name,
                                'type': workflow_type
                            })
                    
                    return matched
            
            return []
        except Exception as e:
            self.logger.log(f"获取工作流列表失败: {e}", 'ERROR')
            return []
    
    def get_workflow_tasks(self, workflow_code):
        """获取工作流的所有任务"""
        try:
            curl_cmd = f"""curl -s "{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/process-definition/{workflow_code}" \
  -H "token: {DS_CONFIG['token']}"""
            
            result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                if response.get('code') == 0:
                    data = response.get('data', {})
                    tasks = data.get('taskDefinitionList', [])
                    return tasks
            
            return []
        except Exception as e:
            self.logger.log(f"获取任务列表失败: {e}", 'ERROR')
            return []
    
    def find_exact_task(self, tasks, table_name):
        """在工作流任务中找到处理特定表的任务"""
        for task in tasks:
            task_name = task.get('name', '')
            task_code = task.get('code')
            task_params = task.get('taskParams', '{}')
            
            # 解析SQL内容
            if isinstance(task_params, str):
                try:
                    task_params = json.loads(task_params)
                except:
                    task_params = {}
            
            raw_script = task_params.get('rawScript', '') if isinstance(task_params, dict) else ''
            
            # 检查SQL是否包含表名（最精确的匹配）
            if table_name.lower() in raw_script.lower():
                return {
                    'code': task_code,
                    'name': task_name,
                    'match_type': 'SQL包含表名'
                }
            
            # 检查任务名是否包含表名关键部分
            # dwd_asset_account_repay -> account_repay
            parts = table_name.split('_')
            if len(parts) >= 3:
                key_part = '_'.join(parts[2:])  # account_repay
                if key_part.lower() in task_name.lower():
                    return {
                        'code': task_code,
                        'name': task_name,
                        'match_type': f'任务名包含{key_part}'
                    }
        
        return None
    
    def start_single_task(self, workflow_code, task_code, task_name, table_name, dt):
        """只启动工作流中的特定任务"""
        self.logger.log(f"启动单任务: {task_name} (表: {table_name}, dt: {dt})")
        
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
                    self.logger.log(f"✅ 任务启动成功: {task_name}, 实例ID: {instance_id}")
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
    
    def repair_table(self, table_info):
        """修复单个表"""
        table_name = table_info['table']
        dt = table_info.get('dt')
        
        if not dt:
            self.logger.log(f"表 {table_name} 没有dt，跳过", 'WARN')
            return False
        
        # 验证dt日期
        try:
            dt_date = datetime.strptime(dt, '%Y-%m-%d')
            today = datetime.now()
            diff_days = (today - dt_date).days
            if diff_days > DAYS_LIMIT or diff_days < 0:
                self.logger.log(f"dt={dt} 超出范围，跳过", 'WARN')
                return False
        except:
            self.logger.log(f"dt格式错误: {dt}", 'ERROR')
            return False
        
        # 第1步：推断工作流类型
        workflow_type = self.infer_workflow_type(table_name)
        if not workflow_type:
            self.logger.log(f"表 {table_name} 无法推断类型，跳过", 'WARN')
            return False
        
        self.logger.log(f"表 {table_name} -> 类型 {workflow_type}")
        
        # 第2步：找到该类型的工作流
        workflows = self.get_workflows_by_type(workflow_type)
        if not workflows:
            self.logger.log(f"找不到 {workflow_type} 类型的工作流", 'WARN')
            return False
        
        self.logger.log(f"找到 {len(workflows)} 个 {workflow_type} 工作流")
        
        # 第3步：在每个工作流内搜索任务
        for workflow in workflows:
            wf_code = workflow['code']
            wf_name = workflow['name']
            
            self.logger.log(f"在工作流 {wf_name} 内搜索任务...")
            
            tasks = self.get_workflow_tasks(wf_code)
            if not tasks:
                continue
            
            # 查找处理该表的任务
            matched_task = self.find_exact_task(tasks, table_name)
            
            if matched_task:
                self.logger.log(f"✅ 找到任务: {matched_task['name']} ({matched_task['match_type']})")
                
                # 第4步：只启动这个任务
                return self.start_single_task(
                    wf_code, 
                    matched_task['code'], 
                    matched_task['name'],
                    table_name, 
                    dt
                )
        
        self.logger.log(f"在所有 {workflow_type} 工作流中都找不到处理 {table_name} 的任务", 'WARN')
        return False
    
    def run(self):
        """运行修复流程"""
        self.logger.log("=" * 80)
        self.logger.log("🚀 智能告警修复启动（精确到表级别任务）")
        self.logger.log("=" * 80)
        
        # 模拟一个测试告警
        test_tables = [
            {
                'table': 'dwd_asset_account_repay',
                'dt': '2026-03-23',
                'alert_id': '9999'
            }
        ]
        
        self.logger.log(f"测试修复 {len(test_tables)} 个表")
        
        for table_info in test_tables:
            success = self.repair_table(table_info)
            if success:
                self.logger.log(f"✅ {table_info['table']} 修复成功")
            else:
                self.logger.log(f"❌ {table_info['table']} 修复失败")
        
        self.logger.log("=" * 80)
        self.logger.log("✅ 流程结束")
        self.logger.log("=" * 80)


if __name__ == "__main__":
    system = SmartRepairSystem()
    system.run()
