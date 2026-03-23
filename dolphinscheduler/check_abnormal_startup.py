#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检测并停止非定时调度启动的工作流实例
用于排查"未上定时却被调度启动"的问题

作者：OpenClaw
日期：2026-03-23
"""

import urllib.request
import urllib.error
import json
import sys
import argparse
from datetime import datetime

# DolphinScheduler 配置
DS_CONFIG = {
    'base_url': 'http://172.20.0.235:12345/dolphinscheduler',
    'token': '0cad23ded0f0e942381fc9717c1581a8',
    'project_code': '158514956085248',
    'project_name': '国内数仓-工作流'
}

# 启动类型映射
COMMAND_TYPES = {
    'SCHEDULER': {'name': '定时调度', 'icon': '⏰', 'normal': True},
    'MANUAL': {'name': '手动触发', 'icon': '👤', 'normal': False},
    'COMPLEMENT_DATA': {'name': '补数据', 'icon': '📅', 'normal': False},
    'START_PROCESS': {'name': 'API启动', 'icon': '🔌', 'normal': False},
    'RETRY': {'name': '故障重试', 'icon': '🔁', 'normal': False},
    'UNKNOWN': {'name': '未知', 'icon': '❓', 'normal': False}
}


def fetch_running_instances():
    """
    获取正在运行的工作流实例
    
    Returns:
        tuple: (success: bool, instances: list)
    """
    url = f"{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/process-instances"
    params = "?stateType=RUNNING_EXECUTION&pageNo=1&pageSize=100"
    
    full_url = url + params
    req = urllib.request.Request(full_url)
    req.add_header('token', DS_CONFIG['token'])
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if result.get('code') == 0:
                instances = result.get('data', {}).get('totalList', [])
                return True, instances
            else:
                print(f"❌ API 错误: {result.get('msg', 'Unknown')}")
                return False, []
                
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False, []


def get_instance_detail(instance_id):
    """
    获取实例详情，包括启动类型
    
    Args:
        instance_id: 工作流实例ID
        
    Returns:
        dict: 实例详情
    """
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
    
    Args:
        instance_id: 实例ID
        
    Returns:
        bool: 是否成功
    """
    url = f"{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/executors/execute"
    
    data = {
        'processInstanceId': instance_id,
        'executeType': 'STOP'  # STOP 或 PAUSE
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'))
    req.add_header('token', DS_CONFIG['token'])
    req.add_header('Content-Type', 'application/json')
    req.method = 'POST'
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('code') == 0:
                return True
            else:
                print(f"  ❌ 停止失败: {result.get('msg')}")
                return False
    except Exception as e:
        print(f"  ❌ 停止异常: {e}")
        return False


def analyze_instances(instances, show_all=False):
    """
    分析实例的启动类型
    
    Args:
        instances: 实例列表
        show_all: 是否显示所有实例（包括定时调度的）
        
    Returns:
        list: 非正常启动的实例
    """
    abnormal_instances = []
    
    print("\n" + "=" * 110)
    print(f"🔍 分析 {len(instances)} 个运行中的实例...")
    print("=" * 110)
    
    for i, inst in enumerate(instances, 1):
        instance_id = inst.get('id')
        name = inst.get('name', 'N/A')
        state = inst.get('state', 'N/A')
        start_time = inst.get('startTime', 'N/A')
        
        # 获取详细信息（包含启动类型）
        detail = get_instance_detail(instance_id)
        command_type = detail.get('commandType', 'UNKNOWN')
        
        # 从COMMAND_TYPES获取信息
        type_info = COMMAND_TYPES.get(command_type, COMMAND_TYPES['UNKNOWN'])
        icon = type_info['icon']
        type_name = type_info['name']
        is_normal = type_info['normal']
        
        # 获取启动用户
        start_user = detail.get('startUser', detail.get('userName', '未知'))
        
        # 获取调度时间（如果是定时调度）
        schedule_time = detail.get('scheduleTime', '')
        
        # 判断是否为异常启动
        if not is_normal:
            abnormal_instances.append({
                'id': instance_id,
                'name': name,
                'type': command_type,
                'type_name': type_name,
                'start_user': start_user,
                'start_time': start_time
            })
        
        # 显示信息
        if show_all or not is_normal:
            print(f"\n[{i}] {icon} {name}")
            print(f"    实例ID: {instance_id}")
            print(f"    启动方式: {type_name} ({command_type})")
            print(f"    启动用户: {start_user}")
            print(f"    开始时间: {start_time}")
            if schedule_time:
                print(f"    调度时间: {schedule_time}")
            print(f"    当前状态: {state}")
            
            if not is_normal:
                print(f"    ⚠️ 警告: 非定时调度启动！")
    
    print("\n" + "=" * 110)
    
    return abnormal_instances


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='检测并停止非定时调度启动的工作流实例',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s                           # 检测非定时启动的实例
  %(prog)s --show-all                # 显示所有运行中的实例
  %(prog)s --stop                    # 停止非定时启动的实例
  %(prog)s --stop --force            # 强制停止（不确认）
        """
    )
    
    parser.add_argument(
        '--show-all',
        action='store_true',
        help='显示所有实例（包括定时调度的）'
    )
    parser.add_argument(
        '--stop',
        action='store_true',
        help='停止非定时调度启动的实例'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='强制停止，不提示确认'
    )
    
    args = parser.parse_args()
    
    # 获取运行中的实例
    print(f"📊 项目: {DS_CONFIG['project_name']}")
    print("🔍 查询正在运行的工作流实例...")
    
    success, instances = fetch_running_instances()
    
    if not success:
        print("❌ 查询失败")
        sys.exit(1)
    
    if not instances:
        print("✅ 当前没有运行中的工作流实例")
        sys.exit(0)
    
    print(f"✅ 找到 {len(instances)} 个运行中的实例\n")
    
    # 分析实例
    abnormal = analyze_instances(instances, show_all=args.show_all)
    
    # 统计
    print(f"\n📊 统计结果:")
    print(f"   总实例数: {len(instances)}")
    print(f"   定时调度: {len(instances) - len(abnormal)}")
    print(f"   非正常启动: {len(abnormal)} ⚠️")
    
    if abnormal:
        print(f"\n⚠️ 发现 {len(abnormal)} 个非定时调度启动的实例:")
        for inst in abnormal:
            print(f"   - {inst['name']} ({inst['type_name']}) 由 {inst['start_user']} 启动")
        
        # 停止实例
        if args.stop:
            print(f"\n🛑 准备停止这些实例...")
            
            if not args.force:
                confirm = input("确认停止以上实例? (yes/no): ")
                if confirm.lower() != 'yes':
                    print("❌ 已取消")
                    sys.exit(0)
            
            stopped_count = 0
            for inst in abnormal:
                print(f"\n🛑 停止实例: {inst['name']} (ID: {inst['id']})")
                if stop_instance(inst['id']):
                    print("   ✅ 停止成功")
                    stopped_count += 1
                else:
                    print("   ❌ 停止失败")
            
            print(f"\n✅ 已成功停止 {stopped_count}/{len(abnormal)} 个实例")
        else:
            print(f"\n💡 使用 --stop 参数可以停止这些实例")
            print(f"   命令: python {sys.argv[0]} --stop")
    else:
        print("\n✅ 所有运行中的实例都是定时调度启动的，正常！")
    
    sys.exit(0)


if __name__ == '__main__':
    main()
