#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检测国内数仓-工作流是否有正在运行的工作流实例
使用标准库 urllib，无需安装 requests

作者：OpenClaw
日期：2026-03-23
"""

import urllib.request
import urllib.error
import json
import sys

# DolphinScheduler 配置
DS_CONFIG = {
    'base_url': 'http://172.20.0.235:12345/dolphinscheduler',
    'token': '0cad23ded0f0e942381fc9717c1581a8',
    'project_code': '158514956085248',  # 国内数仓-工作流
    'project_name': '国内数仓-工作流'
}


def check_running_workflows():
    """
    检测是否有正在运行的工作流实例
    
    Returns:
        tuple: (has_running: bool, count: int)
               has_running 为 None 表示检测失败
    """
    url = f"{DS_CONFIG['base_url']}/projects/{DS_CONFIG['project_code']}/process-instances?stateType=RUNNING_EXECUTION&pageNo=1&pageSize=1"
    
    req = urllib.request.Request(url)
    req.add_header('token', DS_CONFIG['token'])
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if result.get('code') == 0:
                total = result.get('data', {}).get('total', 0)
                return total > 0, total
            else:
                print(f"❌ API 错误: {result.get('msg', 'Unknown')}")
                return None, 0
                
    except urllib.error.URLError as e:
        print(f"❌ 连接失败: {e}")
        return None, 0
    except json.JSONDecodeError:
        print("❌ JSON 解析错误")
        return None, 0
    except Exception as e:
        print(f"❌ 异常: {e}")
        return None, 0


def main():
    """主函数"""
    print(f"🔍 检测项目 [{DS_CONFIG['project_name']}] 是否有运行中的工作流...")
    
    has_running, count = check_running_workflows()
    
    if has_running is None:
        print("⚠️ 检测失败")
        sys.exit(1)
    
    if has_running:
        print(f"🟢 有 {count} 个工作流正在运行")
        return True
    else:
        print("⚪ 没有工作流在运行（空闲状态）")
        return False


if __name__ == '__main__':
    is_running = main()
    # 返回退出码：0=空闲，1=运行中，方便 shell 脚本判断
    sys.exit(1 if is_running else 0)
