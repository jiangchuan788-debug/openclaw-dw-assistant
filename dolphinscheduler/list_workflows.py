#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询国内数仓-工作流项目中的定时任务工作流（已上线的）
支持筛选、排序和详细信息展示

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


def fetch_workflows(filter_name=None, filter_state='ONLINE', limit=50):
    """
    获取工作流定义列表
    
    Args:
        filter_name: 按工作流名称筛选（模糊匹配）
        filter_state: 按状态筛选（ONLINE/OFFLINE）
        limit: 返回的最大数量
        
    Returns:
        tuple: (success: bool, workflows: list, total: int)
    """
    url = f"{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/process-definition"
    params = f"?pageNo=1&pageSize={limit}"
    
    full_url = url + params
    
    req = urllib.request.Request(full_url)
    req.add_header('token', DS_CONFIG['token'])
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if result.get('code') == 0:
                total = result.get('data', {}).get('total', 0)
                workflows = result.get('data', {}).get('totalList', [])
                
                # 按状态筛选
                if filter_state:
                    workflows = [w for w in workflows if w.get('releaseState') == filter_state]
                
                # 按名称筛选
                if filter_name:
                    workflows = [w for w in workflows if filter_name.lower() in w.get('name', '').lower()]
                
                return True, workflows, total
            else:
                print(f"❌ API 错误: {result.get('msg', 'Unknown')}")
                return False, [], 0
                
    except urllib.error.URLError as e:
        print(f"❌ 连接失败: {e}")
        return False, [], 0
    except json.JSONDecodeError:
        print("❌ JSON 解析错误")
        return False, [], 0
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False, [], 0


def get_schedule_info(process_code):
    """获取工作流的定时调度信息"""
    url = f"{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/schedules"
    
    req = urllib.request.Request(url)
    req.add_header('token', DS_CONFIG['token'])
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('code') == 0:
                schedules = result.get('data', {}).get('totalList', [])
                for sch in schedules:
                    if sch.get('processDefinitionCode') == process_code:
                        return sch
            return None
    except:
        return None


def format_time(time_str):
    """格式化时间字符串"""
    if not time_str:
        return "未知"
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return time_str


def display_workflows(workflows, total, show_schedule=False):
    """格式化显示工作流列表"""
    
    print("=" * 110)
    print(f"📊 项目: {DS_CONFIG['project_name']}")
    print(f"📈 工作流总数: {total} 个")
    print("=" * 110)
    
    if not workflows:
        print("\n⚪ 没有匹配的工作流\n")
        return
    
    # 按状态分组统计
    online_count = sum(1 for w in workflows if w.get('releaseState') == 'ONLINE')
    offline_count = sum(1 for w in workflows if w.get('releaseState') == 'OFFLINE')
    
    print(f"\n📋 显示工作流: {len(workflows)} 个")
    print(f"   🟢 已上线(ONLINE): {online_count} 个")
    print(f"   ⚪ 已下线(OFFLINE): {offline_count} 个\n")
    
    # 表头
    print(f"{'序号':<4} {'工作流名称':<45} {'状态':<10} {'版本':<6} {'工作流Code':<20} {'更新时间':<16}")
    print("-" * 110)
    
    # 显示每个工作流
    for i, wf in enumerate(workflows, 1):
        name = wf.get('name', 'N/A')[:43]
        state = wf.get('releaseState', 'N/A')
        version = str(wf.get('version', 'N/A'))
        code = str(wf.get('code', 'N/A'))
        update_time = format_time(wf.get('updateTime', ''))
        
        # 状态图标
        state_icon = "🟢" if state == 'ONLINE' else "⚪"
        
        print(f"{i:<4} {name:<45} {state_icon} {state:<8} {version:<6} {code:<20} {update_time:<16}")
    
    print("=" * 110)
    
    # 显示常用的工作流Code（方便复制使用）
    if len(workflows) <= 10:
        print("\n📋 工作流Code列表（供API调用使用）:")
        for wf in workflows:
            print(f"   {wf.get('name', 'N/A')}: {wf.get('code', 'N/A')}")
        print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='查询国内数仓-工作流项目中的定时任务工作流',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s                           # 显示所有已上线的工作流
  %(prog)s -f "D-1"                  # 筛选名称包含"D-1"的工作流
  %(prog)s -s OFFLINE                # 显示已下线的工作流
  %(prog)s -l 100                    # 显示最多100个工作流
  %(prog)s --list-codes              # 只显示工作流名称和Code
        """
    )
    
    parser.add_argument(
        '-f', '--filter',
        help='按工作流名称筛选（支持模糊匹配）'
    )
    parser.add_argument(
        '-s', '--state',
        choices=['ONLINE', 'OFFLINE'],
        default='ONLINE',
        help='按状态筛选（默认: ONLINE）'
    )
    parser.add_argument(
        '-l', '--limit',
        type=int,
        default=50,
        help='最多显示的工作流数量（默认: 50）'
    )
    parser.add_argument(
        '--list-codes',
        action='store_true',
        help='只显示工作流名称和Code（简洁模式）'
    )
    
    args = parser.parse_args()
    
    # 获取数据
    success, workflows, total = fetch_workflows(
        filter_name=args.filter,
        filter_state=args.state,
        limit=args.limit
    )
    
    if not success:
        print("⚠️ 查询失败")
        sys.exit(1)
    
    # 简洁模式
    if args.list_codes:
        print(f"\n# {DS_CONFIG['project_name']} - 工作流列表\n")
        for wf in workflows:
            name = wf.get('name', 'N/A')
            code = wf.get('code', 'N/A')
            state = wf.get('releaseState', 'N/A')
            print(f"{name}: {code} ({state})")
        print()
        sys.exit(0)
    
    # 详细显示模式
    display_workflows(workflows, total)
    
    # 返回退出码
    sys.exit(0)


if __name__ == '__main__':
    main()
