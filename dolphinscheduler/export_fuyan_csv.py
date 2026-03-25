#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出复验工作流信息到CSV

已知的三个项目:
1. 国内数仓-工作流 (158514956085248)
2. okr_ads (159737550740160)
3. 国内数仓-质量校验 (158515019231232)
"""

import urllib.request
import json
import csv
from datetime import datetime

# DolphinScheduler 配置
DS_CONFIG = {
    'base_url': 'http://172.20.0.235:12345/dolphinscheduler',
    'token': os.environ.get('DS_TOKEN', '')
}

# 三个已知项目
PROJECTS = [
    {'name': '国内数仓-工作流', 'code': '158514956085248'},
    {'name': 'okr_ads', 'code': '159737550740160'},
    {'name': '国内数仓-质量校验', 'code': '158515019231232'}
]


def fetch_project_workflows(project_code):
    """获取指定项目的所有工作流"""
    all_workflows = []
    page_no = 1
    page_size = 50
    
    while True:
        url = f"{DS_CONFIG['base_url']}/projects/{project_code}/process-definition"
        params = f"?pageNo={page_no}&pageSize={page_size}"
        
        req = urllib.request.Request(url + params)
        req.add_header('token', DS_CONFIG['token'])
        
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if result.get('code') == 0:
                    workflows = result.get('data', {}).get('totalList', [])
                    total = result.get('data', {}).get('total', 0)
                    
                    if not workflows:
                        break
                    
                    all_workflows.extend(workflows)
                    
                    if len(all_workflows) >= total:
                        break
                    
                    page_no += 1
                else:
                    break
        except:
            break
    
    return all_workflows


def parse_schedule_info(name):
    """
    从工作流名称解析调度信息
    例如："每日复验全级别数据(W-1)" -> 周期: 每日, 级别: 全级别
    """
    info = {
        '调度周期': '未知',
        '表级别': '未知',
        '任务类型': '复验'
    }
    
    # 解析调度周期
    if '每小时' in name or 'H-1' in name:
        info['调度周期'] = '每小时'
    elif '每4小时' in name:
        info['调度周期'] = '每4小时'
    elif '每12小时' in name:
        info['调度周期'] = '每12小时'
    elif '两小时' in name or '2小时' in name:
        info['调度周期'] = '每2小时'
    elif '每日' in name or '每天' in name or 'D-1' in name:
        info['调度周期'] = '每日'
    elif '每周' in name or 'W-1' in name:
        info['调度周期'] = '每周'
    elif '每月' in name or 'M-3' in name or 'Y-2' in name:
        info['调度周期'] = '每月'
    
    # 解析表级别
    if '1级' in name or '一级' in name:
        info['表级别'] = '1级表'
    elif '2级' in name or '二级' in name:
        info['表级别'] = '2级表'
    elif '3级' in name or '三级' in name:
        info['表级别'] = '3级表'
    elif '全级别' in name:
        info['表级别'] = '全级别'
    
    return info


def export_fuyan_to_csv():
    """导出复验工作流到CSV"""
    print("=" * 80)
    print("📊 导出'复验'工作流信息到CSV")
    print("=" * 80)
    print()
    
    all_fuyan = []
    
    for project in PROJECTS:
        project_name = project['name']
        project_code = project['code']
        
        print(f"📁 查询项目: {project_name}")
        
        # 获取工作流
        workflows = fetch_project_workflows(project_code)
        
        # 筛选包含"复验"的工作流
        fuyan_workflows = [w for w in workflows if '复验' in w.get('name', '')]
        
        for wf in fuyan_workflows:
            name = wf.get('name', 'N/A')
            wf_code = wf.get('code', 'N/A')
            state = wf.get('releaseState', 'N/A')
            version = wf.get('version', 'N/A')
            create_time = wf.get('createTime', 'N/A')
            update_time = wf.get('updateTime', 'N/A')
            description = wf.get('description', '')
            
            # 解析调度信息
            schedule_info = parse_schedule_info(name)
            
            all_fuyan.append({
                '项目名称': project_name,
                '项目Code': project_code,
                '工作流名称': name,
                '工作流Code': wf_code,
                '状态': state,
                '版本': version,
                '任务类型': schedule_info['任务类型'],
                '调度周期': schedule_info['调度周期'],
                '表级别': schedule_info['表级别'],
                '创建时间': create_time,
                '更新时间': update_time,
                '描述': description
            })
    
    if not all_fuyan:
        print("❌ 没有找到'复验'工作流")
        return
    
    # 生成CSV文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'/home/node/.openclaw/workspace/dolphinscheduler/fuyan_workflows_{timestamp}.csv'
    
    # 写入CSV
    fieldnames = [
        '项目名称', '项目Code', '工作流名称', '工作流Code',
        '状态', '版本', '任务类型', '调度周期', '表级别',
        '创建时间', '更新时间', '描述'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_fuyan)
    
    # 输出报告
    print()
    print("=" * 80)
    print("✅ 导出完成")
    print("=" * 80)
    print(f"\n📁 CSV文件: {output_file}")
    print(f"📊 共导出 {len(all_fuyan)} 个'复验'工作流\n")
    
    # 显示内容预览
    print("📋 内容预览:")
    print("-" * 80)
    print(f"{'序号':<4} {'项目名称':<18} {'工作流名称':<35} {'调度周期':<10} {'表级别':<10}")
    print("-" * 80)
    
    for i, wf in enumerate(all_fuyan, 1):
        proj = wf['项目名称'][:16]
        name = wf['工作流名称'][:33]
        period = wf['调度周期']
        level = wf['表级别']
        print(f"{i:<4} {proj:<18} {name:<35} {period:<10} {level:<10}")
    
    print()
    print("=" * 80)
    print("💡 CSV文件包含以下字段:")
    print("   项目名称、项目Code、工作流名称、工作流Code")
    print("   状态、版本、任务类型、调度周期、表级别")
    print("   创建时间、更新时间、描述")
    print("=" * 80)


if __name__ == '__main__':
    export_fuyan_to_csv()
