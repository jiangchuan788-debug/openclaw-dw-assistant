#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常调度实例自动检测与停止脚本（CSV版本）
使用本地CSV文件中的调度配置进行检测，避免API分页问题

异常定义:
1. 无定时配置但被调度启动
2. 调度已下线但仍被启动

作者: OpenClaw
日期: 2026-03-25
"""

import sys
sys.path.insert(0, '/home/node/.openclaw/workspace')
import auto_load_env

import os
import urllib.request
import urllib.error
import json
import subprocess
import csv
from datetime import datetime

# DolphinScheduler 配置
DS_CONFIG = {
    'base_url': 'http://172.20.0.235:12345/dolphinscheduler',
    'token': os.environ.get('DS_TOKEN', ''),
    'project_code': '158514956085248',
    'project_name': '国内数仓-工作流'
}

# TV API配置
TV_API_URL = 'https://tv-service-alert.kuainiu.chat/alert/v2/array'
TV_BOT_ID = 'fbbcabb4-d187-4d9e-8e1e-ba7654a24d1c'

# 钉钉配置
DINGTALK_CONV_ID = 'cidune9y06rl1j0uelxqielqw=='

# CSV文件路径
SCHEDULES_CSV = '/home/node/.openclaw/workspace/dolphinscheduler/schedules_export.csv'


def send_dingtalk(msg):
    """发送钉钉消息"""
    try:
        subprocess.run([
            'openclaw', 'message', 'send',
            '--channel', 'dingtalk-connector',
            '--target', f'group:{DINGTALK_CONV_ID}',
            '--message', msg
        ], capture_output=True, timeout=10)
    except:
        pass


def send_tv_report(message):
    """发送TV报告"""
    try:
        payload = {
            'botId': TV_BOT_ID,
            'message': message,
            'mentions': []
        }
        json_data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        
        req = urllib.request.Request(
            TV_API_URL,
            data=json_data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.getcode() == 202
    except:
        return False


def load_schedules_from_csv():
    """从CSV文件加载调度配置"""
    schedules = {}
    
    if not os.path.exists(SCHEDULES_CSV):
        print(f"⚠️ 警告: CSV文件不存在 {SCHEDULES_CSV}")
        return schedules
    
    try:
        with open(SCHEDULES_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get('工作流Code', '')
                if code:
                    schedules[code] = {
                        'name': row.get('工作流名称', ''),
                        'cron': row.get('Cron表达式', ''),
                        'status': row.get('状态', 'OFFLINE')
                    }
        print(f"✅ 从CSV加载了 {len(schedules)} 个调度配置")
    except Exception as e:
        print(f"❌ 读取CSV失败: {e}")
    
    return schedules


def fetch_running_instances():
    """获取正在运行的工作流实例"""
    url = f"{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/process-instances"
    params = "?stateType=RUNNING_EXECUTION&pageNo=1&pageSize=100"
    
    req = urllib.request.Request(url + params)
    req.add_header('token', DS_CONFIG['token'])
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('code') == 0:
                return True, result.get('data', {}).get('totalList', [])
    except Exception as e:
        print(f"❌ 查询实例失败: {e}")
    
    return False, []


def get_instance_detail(instance_id):
    """获取实例详情"""
    url = f"{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/process-instances/{instance_id}"
    
    req = urllib.request.Request(url)
    req.add_header('token', DS_CONFIG['token'])
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('code') == 0:
                return result.get('data', {})
    except Exception as e:
        print(f"  ⚠️ 获取实例详情失败: {e}")
    
    return {}


def check_workflow_schedule(process_code, schedules_dict):
    """检查工作流是否有定时调度配置（从CSV）"""
    code_str = str(process_code)
    
    if code_str in schedules_dict:
        sch = schedules_dict[code_str]
        return {
            'has_schedule': True,
            'schedule_status': sch.get('status', 'OFFLINE'),
            'cron': sch.get('cron', 'N/A'),
            'schedule_name': sch.get('name', 'N/A')
        }
    
    return {
        'has_schedule': False,
        'schedule_status': 'NONE',
        'cron': 'N/A',
        'schedule_name': 'N/A'
    }


def stop_instance(instance_id):
    """停止工作流实例"""
    url = f"{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/executors/execute"
    
    data = {
        'processInstanceId': instance_id,
        'executeType': 'STOP'
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    req.add_header('token', DS_CONFIG['token'])
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('code') == 0
    except Exception as e:
        print(f"  ❌ 停止异常: {e}")
        return False


def main():
    """主函数"""
    print("="*80)
    print("🔍 异常调度实例自动检测与停止（CSV版本）")
    print("="*80)
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 调度配置CSV: {SCHEDULES_CSV}")
    print("")
    
    # 从CSV加载调度配置
    schedules_dict = load_schedules_from_csv()
    
    if not schedules_dict:
        print("❌ 无法加载调度配置，请检查CSV文件是否存在")
        return
    
    # 获取运行中的实例
    success, instances = fetch_running_instances()
    if not success:
        print("❌ 查询实例失败")
        return
    
    if not instances:
        print("✅ 当前没有运行中的工作流实例")
        # 钉钉：发送空报告
        report = f"""📊 异常调度检测报告

⏰ 检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
✅ 状态: 无运行中实例
💡 未发现异常调度任务"""
        send_dingtalk(report)
        # TV：不发送（无异常）
        print("ℹ️ TV报告未发送（无异常）")
        return
    
    print(f"📋 发现 {len(instances)} 个运行中的实例\n")
    
    abnormal_instances = []
    normal_count = 0
    stopped_count = 0
    
    for i, inst in enumerate(instances, 1):
        instance_id = inst.get('id')
        name = inst.get('name', 'N/A')
        process_code = inst.get('processDefinitionCode')
        start_time = inst.get('startTime', 'N/A')
        
        # 获取实例详情
        detail = get_instance_detail(instance_id)
        command_type = detail.get('commandType', 'UNKNOWN')
        
        print(f"[{i}/{len(instances)}] 检查: {name[:40]}")
        print(f"    实例ID: {instance_id}")
        print(f"    启动类型: {command_type}")
        
        # 只有 SCHEDULER 类型的才需要检查
        if command_type == 'SCHEDULER':
            # 从CSV检查调度配置
            schedule_info = check_workflow_schedule(process_code, schedules_dict)
            
            has_schedule = schedule_info['has_schedule']
            schedule_status = schedule_info['schedule_status']
            
            print(f"    定时配置: {'有' if has_schedule else '无'}")
            if has_schedule:
                print(f"    调度状态: {schedule_status}")
            
            # 判断是否为异常
            is_abnormal = False
            abnormal_reason = ""
            
            if not has_schedule:
                is_abnormal = True
                abnormal_reason = "无定时配置但被调度启动"
            elif schedule_status == 'OFFLINE':
                is_abnormal = True
                abnormal_reason = "调度已下线但仍被启动"
            
            if is_abnormal:
                print(f"    ⚠️ 异常: {abnormal_reason}")
                print(f"    🛑 正在停止...")
                
                # 自动停止（无需确认）
                if stop_instance(instance_id):
                    print(f"    ✅ 停止成功")
                    stopped_count += 1
                    abnormal_instances.append({
                        'id': instance_id,
                        'name': name,
                        'reason': abnormal_reason,
                        'start_time': start_time,
                        'stopped': True
                    })
                else:
                    print(f"    ❌ 停止失败")
                    abnormal_instances.append({
                        'id': instance_id,
                        'name': name,
                        'reason': abnormal_reason,
                        'start_time': start_time,
                        'stopped': False
                    })
            else:
                print(f"    ✅ 正常")
                normal_count += 1
        else:
            # 非调度启动的，直接认为是正常的
            print(f"    ✅ 正常: {command_type}")
            normal_count += 1
        
        print()
    
    # 生成钉钉报告（始终发送）
    report_lines = ["📊 异常调度检测与停止报告", ""]
    report_lines.append(f"⏰ 检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    report_lines.append(f"📋 总实例数: {len(instances)}")
    report_lines.append(f"✅ 正常实例: {normal_count}")
    report_lines.append(f"⚠️ 异常实例: {len(abnormal_instances)}")
    
    if abnormal_instances:
        report_lines.append("")
        report_lines.append(f"🛑 已停止异常实例 ({stopped_count}/{len(abnormal_instances)}):")
        for inst in abnormal_instances:
            status = "✅已停" if inst['stopped'] else "❌失败"
            report_lines.append(f"  • {inst['name']} [{status}]")
            report_lines.append(f"    原因: {inst['reason']}")
            report_lines.append(f"    ID: {inst['id']}")
    else:
        report_lines.append("")
        report_lines.append("✅ 未发现异常调度任务")
    
    ding_report = "\n".join(report_lines)
    
    # 发送钉钉报告
    print("="*80)
    print("📤 发送报告...")
    send_dingtalk(ding_report)
    print("✅ 钉钉报告已发送")
    
    # TV：只在有异常需要通知时发送
    if abnormal_instances:
        tv_lines = ["📊 异常调度检测与停止报告", ""]
        tv_lines.append(f"⏰ 检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        tv_lines.append("")
        
        for inst in abnormal_instances:
            if inst['stopped']:
                tv_lines.append(f"✅ 已停止: {inst['name']}")
            else:
                tv_lines.append(f"❌ 停止失败: {inst['name']} (需人工处理)")
            tv_lines.append(f"   原因: {inst['reason']}")
        
        tv_report = "\n".join(tv_lines)
        send_tv_report(tv_report)
        print("✅ TV报告已发送（有异常需通知）")
    else:
        print("ℹ️ TV报告未发送（无异常）")
    
    print("="*80)


if __name__ == '__main__':
    main()
