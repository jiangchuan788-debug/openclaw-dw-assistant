#!/usr/bin/env python3
"""
定时任务导出脚本
将OpenClaw定时任务导出为CSV，方便管理和查看
"""

import json
import csv
from datetime import datetime
import os

# 导出文件路径
EXPORT_DIR = '/home/node/.openclaw/workspace/cron_jobs'

def export_cron_jobs_to_csv(jobs_data, filename=None):
    """导出定时任务到CSV"""
    
    if filename is None:
        filename = f"cron_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    filepath = os.path.join(EXPORT_DIR, filename)
    
    # 确保目录存在
    os.makedirs(EXPORT_DIR, exist_ok=True)
    
    # CSV表头
    headers = [
        '任务ID', '任务名称', '状态', 'Cron表达式', '时区', 
        '下次执行时间', '上次执行时间', '上次执行状态',
        '执行超时(秒)', '投递模式', '投递渠道', '会话目标'
    ]
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for job in jobs_data.get('jobs', []):
            # 解析调度信息
            schedule = job.get('schedule', {})
            state = job.get('state', {})
            payload = job.get('payload', {})
            delivery = job.get('delivery', {})
            
            # 转换时间戳
            next_run = state.get('nextRunAtMs')
            last_run = state.get('lastRunAtMs')
            
            next_run_str = datetime.fromtimestamp(next_run/1000).strftime('%Y-%m-%d %H:%M:%S') if next_run else 'N/A'
            last_run_str = datetime.fromtimestamp(last_run/1000).strftime('%Y-%m-%d %H:%M:%S') if last_run else 'N/A'
            
            row = [
                job.get('id', ''),
                job.get('name', ''),
                '启用' if job.get('enabled') else '禁用',
                schedule.get('expr', ''),
                schedule.get('tz', ''),
                next_run_str,
                last_run_str,
                state.get('lastRunStatus', 'N/A'),
                payload.get('timeoutSeconds', ''),
                delivery.get('mode', ''),
                delivery.get('channel', ''),
                job.get('sessionTarget', '')
            ]
            writer.writerow(row)
    
    return filepath


def load_cron_jobs_from_csv(filename):
    """从CSV加载定时任务信息"""
    filepath = os.path.join(EXPORT_DIR, filename)
    
    if not os.path.exists(filepath):
        return None
    
    jobs = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            jobs.append(row)
    
    return jobs


if __name__ == '__main__':
    # 示例：导出当前定时任务
    # 实际使用时从API获取
    print("定时任务CSV导出工具")
    print(f"导出目录: {EXPORT_DIR}")
