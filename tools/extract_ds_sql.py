#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DolphinScheduler 工作流 SQL 提取工具
通过 API 拉取指定项目下所有工作流的 SQL 代码

作者: OpenClaw
日期: 2026-03-26
"""

import sys
sys.path.insert(0, '/home/node/.openclaw/workspace')
import auto_load_env

import os
import json
import urllib.request
import urllib.error
from datetime import datetime

# DolphinScheduler 配置
DS_BASE_URL = 'http://172.20.0.235:12345/dolphinscheduler'
DS_TOKEN = os.environ.get('DS_TOKEN', '')


def ds_api_get(endpoint):
    """发送 GET 请求到 DS API"""
    url = f"{DS_BASE_URL}{endpoint}"
    req = urllib.request.Request(url)
    req.add_header('token', DS_TOKEN)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('code') == 0:
                return True, result.get('data', {})
            else:
                return False, result.get('msg', 'Unknown error')
    except Exception as e:
        return False, str(e)


def get_project_workflows(project_code):
    """获取项目下的所有工作流列表 (DS 3.3.0: workflow-definition)"""
    success, data = ds_api_get(f"/projects/{project_code}/workflow-definition?pageNo=1&pageSize=100")
    
    if not success:
        print(f"❌ 获取工作流列表失败: {data}")
        return []
    
    workflows = data.get('totalList', [])
    print(f"✅ 找到 {len(workflows)} 个工作流")
    return workflows


def get_workflow_detail(project_code, workflow_code):
    """获取工作流详细信息（包含任务定义） (DS 3.3.0: workflow-definition)"""
    success, data = ds_api_get(f"/projects/{project_code}/workflow-definition/{workflow_code}")
    
    if not success:
        print(f"❌ 获取工作流详情失败: {data}")
        return None
    
    return data


def extract_sql_from_workflow(workflow_detail):
    """从工作流详情中提取 SQL 代码"""
    sql_tasks = []
    
    process_def = workflow_detail.get('processDefinition', {})
    task_definitions = workflow_detail.get('taskDefinitionList', [])
    
    workflow_name = process_def.get('name', 'Unknown')
    workflow_code = process_def.get('code', '')
    
    for task in task_definitions:
        task_type = task.get('taskType', '')
        task_name = task.get('name', '')
        task_code = task.get('code', '')
        
        # 只提取 SQL 类型的任务
        if task_type.upper() in ['SQL', 'SQLODT', 'SQLPRESTO', 'SQLFLINK', 'SQLSPARK']:
            task_params = task.get('taskParams', {})
            sql_content = task_params.get('sql', '')
            
            if sql_content and sql_content.strip():
                sql_tasks.append({
                    'workflow_name': workflow_name,
                    'workflow_code': workflow_code,
                    'task_name': task_name,
                    'task_code': task_code,
                    'task_type': task_type,
                    'datasource': task_params.get('datasource', ''),
                    'sql': sql_content.strip()
                })
    
    return sql_tasks


def save_sql_to_file(project_name, workflow_name, task_name, sql_content, output_dir):
    """保存 SQL 到文件"""
    # 清理文件名中的非法字符
    safe_workflow_name = "".join(c for c in workflow_name if c.isalnum() or c in ('_', '-')).strip()
    safe_task_name = "".join(c for c in task_name if c.isalnum() or c in ('_', '-')).strip()
    
    filename = f"{safe_workflow_name}_{safe_task_name}.sql"
    filepath = os.path.join(output_dir, filename)
    
    # 添加文件头注释
    header = f"""-- Workflow: {workflow_name}
-- Task: {task_name}
-- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- {'='*60}

"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(header)
        f.write(sql_content)
    
    return filepath


def extract_project_sql(project_code, project_name=None, output_dir=None):
    """
    提取指定项目下所有工作流的 SQL
    
    Args:
        project_code: 项目 Code (如 159737550740160)
        project_name: 项目名称（用于输出目录命名）
        output_dir: 输出目录（可选，默认生成）
    
    Returns:
        提取的 SQL 任务数量
    """
    if not output_dir:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dir_name = project_name if project_name else f"project_{project_code}"
        output_dir = f"/home/node/.openclaw/workspace/sql_export/{dir_name}_{timestamp}"
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("="*70)
    print(f"🚀 开始提取项目 SQL")
    print(f"项目 Code: {project_code}")
    print(f"输出目录: {output_dir}")
    print("="*70)
    print()
    
    # 1. 获取所有工作流
    print("📋 步骤1: 获取工作流列表...")
    workflows = get_project_workflows(project_code)
    
    if not workflows:
        print("❌ 未找到工作流，退出")
        return 0
    
    print()
    
    # 2. 遍历每个工作流，提取 SQL
    all_sql_tasks = []
    
    for i, workflow in enumerate(workflows, 1):
        workflow_name = workflow.get('name', 'Unknown')
        workflow_code = workflow.get('code', '')
        
        print(f"[{i}/{len(workflows)}] 处理工作流: {workflow_name}")
        print(f"    Code: {workflow_code}")
        
        # 获取工作流详情
        detail = get_workflow_detail(project_code, workflow_code)
        if not detail:
            print(f"    ⚠️ 跳过（获取详情失败）")
            continue
        
        # 提取 SQL
        sql_tasks = extract_sql_from_workflow(detail)
        
        if sql_tasks:
            print(f"    ✅ 找到 {len(sql_tasks)} 个 SQL 任务")
            for task in sql_tasks:
                # 保存到文件
                filepath = save_sql_to_file(
                    project_name or project_code,
                    task['workflow_name'],
                    task['task_name'],
                    task['sql'],
                    output_dir
                )
                print(f"       💾 已保存: {os.path.basename(filepath)}")
                all_sql_tasks.append(task)
        else:
            print(f"    ℹ️ 无 SQL 任务")
        
        print()
    
    # 3. 生成汇总报告
    print("="*70)
    print("📊 提取完成统计")
    print("="*70)
    print(f"项目: {project_name or project_code}")
    print(f"工作流总数: {len(workflows)}")
    print(f"SQL 任务总数: {len(all_sql_tasks)}")
    print(f"输出目录: {output_dir}")
    print("="*70)
    
    return len(all_sql_tasks)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='提取 DolphinScheduler 项目中的 SQL')
    parser.add_argument('project_code', type=str, help='项目 Code (如 159737550740160)')
    parser.add_argument('--name', type=str, help='项目名称（用于命名输出目录）')
    parser.add_argument('--output', type=str, help='输出目录（可选）')
    
    args = parser.parse_args()
    
    if not DS_TOKEN:
        print("❌ 错误: DS_TOKEN 环境变量未设置")
        print("请执行: export DS_TOKEN='your_token'")
        return
    
    count = extract_project_sql(
        project_code=args.project_code,
        project_name=args.name,
        output_dir=args.output
    )
    
    if count > 0:
        print(f"\n✅ 成功提取 {count} 个 SQL 任务")
    else:
        print("\n⚠️ 未提取到 SQL 任务")


if __name__ == '__main__':
    main()
