#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常调度实例自动检测与停止脚本（全覆盖版本）
规则：所有运行中实例，只要在CSV中不存在且是调度启动，就停止

作者: OpenClaw
日期: 2026-03-26
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
    """从CSV文件加载所有调度配置（只保存Code）"""
    schedule_codes = set()
    
    if not os.path.exists(SCHEDULES_CSV):
        print(f"⚠️ 警告: CSV文件不存在 {SCHEDULES_CSV}")
        return schedule_codes
    
    try:
        with open(SCHEDULES_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get('工作流Code', '').strip()
                if code:
                    schedule_codes.add(code)
        print(f"✅ 从CSV加载了 {len(schedule_codes)} 个调度配置")
        print(f"📋 调度Code列表: {sorted(schedule_codes)[:5]}... (显示前5个)")
    except Exception as e:
        print(f"❌ 读取CSV失败: {e}")
    
    return schedule_codes


def fetch_running_instances():
    """获取所有运行中的工作流实例（多页查询）"""
    all_instances = []
    page_no = 1
    page_size = 100
    
    while True:
        url = f"{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/process-instances"
        params = f"?stateType=RUNNING_EXECUTION&pageNo={page_no}&pageSize={page_size}"
        
        req = urllib.request.Request(url + params)
        req.add_header('token', DS_CONFIG['token'])
        
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get('code') == 0:
                    instances = result.get('data', {}).get('totalList', [])
                    all_instances.extend(instances)
                    
                    # 检查是否还有更多页
                    total = result.get('data', {}).get('total', 0)
                    if page_no * page_size >= total or len(instances) < page_size:
                        break
                    page_no += 1
                else:
                    break
        except Exception as e:
            print(f"❌ 查询实例失败: {e}")
            break
    
    return all_instances


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


def stop_instance(instance_id):
    """
    停止工作流实例
    API: POST /projects/{code}/executors/execute
    """
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
            success = result.get('code') == 0
            if not success:
                print(f"  ⚠️ 停止失败: {result.get('msg', '未知错误')}")
            return success
    except Exception as e:
        print(f"  ❌ 停止异常: {e}")
        return False


def main():
    """主函数 - 全覆盖检测与停止"""
    print("="*80)
    print("🔍 异常调度实例全覆盖检测与停止")
    print("="*80)
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 调度配置CSV: {SCHEDULES_CSV}")
    print(f"📝 规则: CSV中不存在 + SCHEDULER启动 → 停止")
    print("")
    
    # 从CSV加载所有调度配置Code
    schedule_codes = load_schedules_from_csv()
    
    if not schedule_codes:
        print("❌ 无法加载调度配置，退出")
        return
    
    # 获取所有运行中的实例
    instances = fetch_running_instances()
    
    if not instances:
        print("✅ 当前没有运行中的工作流实例")
        report = f"""📊 异常调度全覆盖检测

⏰ 检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
✅ 状态: 无运行中实例"""
        send_dingtalk(report)
        return
    
    print(f"📋 发现 {len(instances)} 个运行中的实例\n")
    
    # 分类统计
    normal_instances = []      # 正常：在CSV中
    abnormal_stopped = []      # 异常已停止
    abnormal_failed = []       # 异常停止失败
    ignored_instances = []     # 忽略：非SCHEDULER启动
    
    for i, inst in enumerate(instances, 1):
        instance_id = inst.get('id')
        name = inst.get('name', 'N/A')
        process_code = str(inst.get('processDefinitionCode', ''))
        
        print(f"[{i}/{len(instances)}] 检查: {name[:50]}")
        print(f"    实例ID: {instance_id}")
        print(f"    工作流Code: {process_code}")
        
        # 获取实例详情（查看启动类型）
        detail = get_instance_detail(instance_id)
        command_type = detail.get('commandType', 'UNKNOWN')
        
        print(f"    启动类型: {command_type}")
        
        # 检查是否在CSV中
        in_csv = process_code in schedule_codes
        print(f"    CSV中存在: {'✅ 是' if in_csv else '❌ 否'}")
        
        if in_csv:
            # 在CSV中，正常
            print(f"    ✅ 正常（有定时配置）")
            normal_instances.append({
                'id': instance_id,
                'name': name,
                'code': process_code
            })
        elif command_type != 'SCHEDULER':
            # 不在CSV中，但不是调度启动，忽略
            print(f"    ⏭️ 忽略（非调度启动: {command_type}）")
            ignored_instances.append({
                'id': instance_id,
                'name': name,
                'code': process_code,
                'command_type': command_type
            })
        else:
            # 不在CSV中，且是调度启动 → 异常，需要停止
            print(f"    ⚠️ 异常（无配置+调度启动）")
            print(f"    🛑 正在停止...")
            
            if stop_instance(instance_id):
                print(f"    ✅ 停止成功")
                abnormal_stopped.append({
                    'id': instance_id,
                    'name': name,
                    'code': process_code
                })
            else:
                print(f"    ❌ 停止失败")
                abnormal_failed.append({
                    'id': instance_id,
                    'name': name,
                    'code': process_code
                })
        
        print()
    
    # 生成钉钉报告（始终发送）
    report_lines = ["📊 异常调度全覆盖检测报告", ""]
    report_lines.append(f"⏰ 检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"")
    report_lines.append(f"📋 总实例数: {len(instances)}")
    report_lines.append(f"✅ 正常实例: {len(normal_instances)}")
    report_lines.append(f"⏭️ 忽略实例: {len(ignored_instances)} (非调度启动)")
    report_lines.append(f"⚠️ 异常已停止: {len(abnormal_stopped)}")
    report_lines.append(f"❌ 异常停止失败: {len(abnormal_failed)}")
    
    if abnormal_stopped:
        report_lines.append("")
        report_lines.append("🛑 已停止的异常实例:")
        for inst in abnormal_stopped:
            report_lines.append(f"  • {inst['name']}")
            report_lines.append(f"    ID: {inst['id']} | Code: {inst['code']}")
    
    if abnormal_failed:
        report_lines.append("")
        report_lines.append("❌ 停止失败的异常实例:")
        for inst in abnormal_failed:
            report_lines.append(f"  • {inst['name']}")
            report_lines.append(f"    ID: {inst['id']} | Code: {inst['code']}")
    
    ding_report = "\n".join(report_lines)
    
    # 发送报告
    print("="*80)
    print("📤 发送报告...")
    send_dingtalk(ding_report)
    print("✅ 钉钉报告已发送")
    
    # TV：有异常时发送（成功停止或停止失败）
    if abnormal_stopped or abnormal_failed:
        tv_lines = ["📊 异常调度检测与停止报告", ""]
        tv_lines.append(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        tv_lines.append("")
        
        if abnormal_stopped:
            tv_lines.append(f"✅ 已停止 {len(abnormal_stopped)} 个:")
            for inst in abnormal_stopped:
                tv_lines.append(f"  • {inst['name']}")
        
        if abnormal_failed:
            tv_lines.append(f"❌ 停止失败 {len(abnormal_failed)} 个:")
            for inst in abnormal_failed:
                tv_lines.append(f"  • {inst['name']}")
        
        tv_report = "\n".join(tv_lines)
        send_tv_report(tv_report)
        print("✅ TV报告已发送（有异常需通知）")
    else:
        print("ℹ️ TV报告未发送（无异常）")
    
    print("="*80)


if __name__ == '__main__':
    main()
