#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出国内数仓-工作流项目中的所有工作流列表（名称和Code对应关系）
生成CSV文件

作者：OpenClaw
日期：2026-03-23
"""

import os
import urllib.request
import json
import csv
import sys

# DolphinScheduler 配置
DS_CONFIG = {
    'base_url': 'http://172.20.0.235:12345/dolphinscheduler',
    'token': os.environ.get('DS_TOKEN', ''),
    'project_code': '158514956085248',
    'project_name': '国内数仓-工作流'
}


def fetch_all_workflows():
    """获取所有工作流（支持分页）"""
    all_workflows = []
    page_no = 1
    page_size = 50
    
    while True:
        url = f"{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/process-definition"
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
                    print(f"  获取第 {page_no} 页: {len(workflows)} 个工作流")
                    
                    # 检查是否获取完毕
                    if len(all_workflows) >= total:
                        break
                    
                    page_no += 1
                else:
                    print(f"❌ API 错误: {result.get('msg')}")
                    break
        except Exception as e:
            print(f"❌ 异常: {e}")
            break
    
    return all_workflows


def export_to_csv(workflows, output_file):
    """导出工作流到CSV文件"""
    
    # 准备数据
    data = []
    for i, wf in enumerate(workflows, 1):
        data.append({
            '序号': i,
            '工作流名称': wf.get('name', 'N/A'),
            '工作流Code': wf.get('code', 'N/A'),
            '状态': wf.get('releaseState', 'N/A'),
            '版本': wf.get('version', 'N/A'),
            '创建时间': wf.get('createTime', 'N/A'),
            '更新时间': wf.get('updateTime', 'N/A'),
            '描述': wf.get('description', '')
        })
    
    # 写入CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['序号', '工作流名称', '工作流Code', '状态', '版本', '创建时间', '更新时间', '描述']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(data)
    
    return data


def main():
    print("=" * 80)
    print(f"📊 导出工作流列表")
    print(f"项目: {DS_CONFIG['project_name']}")
    print("=" * 80)
    print()
    
    # 获取所有工作流
    print("🔍 查询工作流列表...")
    workflows = fetch_all_workflows()
    
    if not workflows:
        print("❌ 未获取到工作流数据")
        sys.exit(1)
    
    print(f"\n✅ 共获取到 {len(workflows)} 个工作流\n")
    
    # 导出到CSV
    output_file = '/home/node/.openclaw/workspace/dolphinscheduler/workflows_export.csv'
    data = export_to_csv(workflows, output_file)
    
    print("=" * 80)
    print("📋 导出结果")
    print("=" * 80)
    print(f"   文件路径: {output_file}")
    print(f"   工作流总数: {len(workflows)}")
    print()
    
    # 显示前20个工作流
    print("📋 前20个工作流预览:")
    print("-" * 80)
    print(f"{'序号':<6} {'工作流名称':<45} {'工作流Code':<20} {'状态':<10}")
    print("-" * 80)
    
    for item in data[:20]:
        name = item['工作流名称'][:43] if len(item['工作流名称']) > 43 else item['工作流名称']
        print(f"{item['序号']:<6} {name:<45} {item['工作流Code']:<20} {item['状态']:<10}")
    
    if len(data) > 20:
        print(f"\n... 还有 {len(data) - 20} 个工作流")
    
    print()
    print("=" * 80)
    print(f"✅ CSV文件已生成: {output_file}")
    print("=" * 80)


if __name__ == '__main__':
    main()
