#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索三个项目中的所有"复验"工作流

已知的三个项目:
1. 国内数仓-工作流 (158514956085248)
2. okr_ads (159737550740160)
3. 国内数仓-质量校验 (158515019231232)

作者：OpenClaw
日期：2026-03-23
"""

import os
import urllib.request
import json

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


def search_fuyan_workflows():
    """搜索所有项目中的'复验'工作流"""
    print("=" * 100)
    print("🔍 搜索三个项目中的'复验'工作流")
    print("=" * 100)
    print()
    
    all_fuyan = []
    
    for project in PROJECTS:
        project_name = project['name']
        project_code = project['code']
        
        print(f"\n📁 项目: {project_name}")
        print(f"   Code: {project_code}")
        print()
        
        # 获取工作流
        workflows = fetch_project_workflows(project_code)
        
        if not workflows:
            print("   没有找到工作流")
            continue
        
        # 筛选包含"复验"的工作流
        fuyan_workflows = [w for w in workflows if '复验' in w.get('name', '')]
        
        if fuyan_workflows:
            print(f"   ✅ 找到 {len(fuyan_workflows)} 个'复验'工作流:")
            for i, wf in enumerate(fuyan_workflows, 1):
                name = wf.get('name', 'N/A')
                code = wf.get('code', 'N/A')
                state = wf.get('releaseState', 'N/A')
                print(f"      {i}. {name}")
                print(f"         Code: {code} | 状态: {state}")
                
                # 记录到总列表
                all_fuyan.append({
                    'project_name': project_name,
                    'project_code': project_code,
                    'workflow_name': name,
                    'workflow_code': code,
                    'status': state
                })
        else:
            print(f"   ⚪ 没有'复验'工作流")
    
    # 汇总报告
    print("\n" + "=" * 100)
    print("📊 汇总报告")
    print("=" * 100)
    print(f"\n总计找到 {len(all_fuyan)} 个'复验'工作流\n")
    
    if all_fuyan:
        print(f"{'序号':<4} {'项目名称':<20} {'工作流名称':<40} {'工作流Code':<20}")
        print("-" * 100)
        
        for i, wf in enumerate(all_fuyan, 1):
            proj = wf['project_name'][:18]
            name = wf['workflow_name'][:38]
            code = wf['workflow_code']
            print(f"{i:<4} {proj:<20} {name:<40} {code:<20}")
        
        print()
        print("💡 工作流Code可用于启动工作流:")
        print("   python dolphinscheduler_api.py --project <项目Code> --process <工作流Code>")
    
    print("=" * 100)


if __name__ == '__main__':
    search_fuyan_workflows()
