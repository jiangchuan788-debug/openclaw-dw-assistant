#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日总结生成脚本
每天 22:00 自动执行，总结当天的重要事项

使用方法：
1. 配置 cron 定时任务：
   0 22 * * * cd C:\Users\21326\.openclaw\workspace && python daily_summary.py

2. 或者手动执行：
   python daily_summary.py
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# 配置
WORKSPACE_DIR = Path(r"C:\Users\21326\.openclaw\workspace")
MEMORY_DIR = WORKSPACE_DIR / "memory"
SESSIONS_DIR = Path(r"C:\Users\21326\.openclaw\agents\main\sessions")


def get_today_sessions():
    """获取今天的会话记录"""
    today = datetime.now().strftime("%Y-%m-%d")
    sessions = []
    
    # 读取今天的会话日志
    if SESSIONS_DIR.exists():
        for session_file in SESSIONS_DIR.glob("*.jsonl"):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                msg = json.loads(line)
                                if today in msg.get('timestamp', ''):
                                    sessions.append(msg)
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                print(f"读取会话文件失败：{e}")
    
    return sessions


def analyze_sessions(sessions):
    """分析会话记录，提取重要事项"""
    summary = {
        'total_messages': len(sessions),
        'topics': [],
        'tasks_completed': [],
        'files_created': [],
        'errors': [],
        'key_learnings': []
    }
    
    # 简单分析（可以根据需要扩展）
    for msg in sessions:
        content = msg.get('content', '')
        
        # 检测文件创建
        if 'Successfully wrote' in content or '创建' in content:
            summary['files_created'].append(content[:200])
        
        # 检测错误
        if 'Error' in content or '失败' in content or '❌' in content:
            summary['errors'].append(content[:200])
        
        # 检测成功
        if '成功' in content or '✅' in content:
            summary['tasks_completed'].append(content[:200])
    
    return summary


def generate_daily_summary():
    """生成每日总结"""
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    
    print(f"📝 正在生成 {today_str} 的每日总结...")
    
    # 获取会话记录
    sessions = get_today_sessions()
    print(f"   找到 {len(sessions)} 条会话记录")
    
    # 分析会话
    analysis = analyze_sessions(sessions)
    
    # 生成总结内容
    summary_content = f"""# 每日总结 - {today_str}

> **生成时间：** {today.strftime("%Y-%m-%d %H:%M")}  
> **目的：** 记录今天的重要事项，方便回忆和重启后快速恢复记忆

---

## 📋 今日概览

### 时间
- **日期：** {today.strftime("%Y-%m-%d %A")}
- **时区：** Asia/Shanghai (GMT+8)
- **会话数量：** {analysis['total_messages']} 条

### 主要成就
{chr(10).join(['✅ ' + task[:100] for task in analysis['tasks_completed'][:5]]) if analysis['tasks_completed'] else '- 暂无记录'}

---

## 📁 创建的文件

"""
    
    # 查找今天创建的文件
    created_files = []
    for file_path in WORKSPACE_DIR.glob("*.md"):
        if file_path.stat().st_mtime > (today.replace(hour=0, minute=0, second=0).timestamp()):
            created_files.append(f"- `{file_path.name}` - {file_path.stat().st_size:,} 字节")
    
    for file_path in WORKSPACE_DIR.glob("*.py"):
        if file_path.stat().st_mtime > (today.replace(hour=0, minute=0, second=0).timestamp()):
            created_files.append(f"- `{file_path.name}` - {file_path.stat().st_size:,} 字节")
    
    summary_content += "\n".join(created_files) if created_files else "- 暂无新文件"
    
    summary_content += f"""

---

## 🔧 待办事项

### 未完成的任务
- [ ] 待办事项 1
- [ ] 待办事项 2

---

## 💡 今日学习

### 核心知识点
1. 知识点 1
2. 知识点 2
3. 知识点 3

### 踩坑记录
- 问题：描述遇到的问题
- 原因：分析根本原因
- 解决：记录解决方案

---

## 📅 明日计划

1. [ ] 计划 1
2. [ ] 计划 2
3. [ ] 计划 3

---

**生成方式：** 自动生成  
**下次生成：** {(today + timedelta(days=1)).strftime("%Y-%m-%d")} 22:00

"""
    
    # 保存总结
    output_file = MEMORY_DIR / f"daily-summary-{today_str}.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(summary_content)
    
    print(f"✅ 每日总结已保存到：{output_file}")
    
    return output_file


if __name__ == '__main__':
    generate_daily_summary()
