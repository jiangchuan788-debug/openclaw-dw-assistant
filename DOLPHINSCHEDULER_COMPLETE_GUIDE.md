# DolphinScheduler API 调用完全指南

> **从 0 到 1 的完整实践记录**  
> **作者：** 陈江川  
> **日期：** 2026-03-17  
> **版本：** v1.0  
> **适用对象：** OpenClaw 用户、DolphinScheduler 开发者

---

## 📖 文档说明

本文档记录了使用 OpenClaw 调用 DolphinScheduler API 的**完整过程**，包括：
- ✅ 环境探索和 API 发现
- ✅ 参数调试和踩坑记录
- ✅ 最终解决方案
- ✅ 可复用的代码和脚本

**适合人群：**
- 第一次接触 DolphinScheduler API 的开发者
- 需要自动化调度工作流的运维人员
- 想学习 API 调试思路的技术人员

---

## 🎯 学习目标

学完本文档后，你将能够：

1. ✅ 使用 API 启动工作流（整个工作流）
2. ✅ 使用 API 启动单个任务（精准控制）
3. ✅ 传递自定义参数（如业务日期）
4. ✅ 选择不同的执行模式（TASK_ONLY/TASK_POST/TASK_PRE）
5. ✅ 排查常见的 API 调用错误
6. ✅ 使用 Python 或 PowerShell 自动化调用

---

## 📋 目录

1. [背景介绍](#背景介绍)
2. [环境信息](#环境信息)
3. [核心发现](#核心发现)
4. [完整代码](#完整代码)
5. [使用场景](#使用场景)
6. [调试过程](#调试过程)
7. [常见错误](#常见错误)
8. [最佳实践](#最佳实践)

---

## 📖 背景介绍

### 问题起源

我们需要通过 API 自动化启动 DolphinScheduler 工作流，替代手动在 Web UI 点击操作。

**需求：**
1. 启动整个工作流
2. 启动单个任务
3. 传递自定义参数（如 `dt=2026-03-17`）

**挑战：**
- API 文档不完整
- 参数格式要求严格
- 多个"隐藏"必填参数

---

## 🌐 环境信息

### DolphinScheduler 环境

| 配置项 | 值 |
|--------|-----|
| API 地址 | http://127.0.0.1:12345/dolphinscheduler |
| 版本 | 3.x |
| Token | `0cad23ded0f0e942381fc9717c1581a8` |
| 当前用户 | jiangchuanchen (ADMIN_USER) |
| 租户 | dolphinscheduler |

### 测试项目

| 项目名称 | 项目 Code | 说明 |
|----------|-----------|------|
| okr_ads | 159737550740160 | 测试项目 |
| 国内数仓 - 工作流 | 158514956085248 | 生产项目 |

### 测试工作流

| 工作流 Code | 工作流名称 | 任务数 | 说明 |
|-------------|-----------|--------|------|
| 168243093291713 | (乱码) | 2 | 测试工作流 |
| - market_fee_by_channel | 168243093291712 | SQL 任务 |
| - market_fee_by_channel_2 | 168251685969600 | SQL 任务 |

### 可用环境

| 环境名称 | 环境 Code | 用途 |
|----------|-----------|------|
| prod | 154818922491872 | 生产环境 |
| develop | 154818735899616 | 开发环境 |
| global | 154818709784544 | 全局环境 |

---

## 💡 核心发现

### 发现 1：scheduleTime 是必填参数 ⭐⭐⭐

**问题：** API 调用返回 50014 错误，但 Web UI 启动正常

**根因：** Spring Boot 框架强制校验 `scheduleTime` 参数，即使为空也必须传

**解决方案：**
```python
body['scheduleTime'] = ""  # 必须传空字符串！
```

**排查过程：**
- 尝试了 7 种参数组合都失败
- 查看服务端日志发现 `MissingServletRequestParameterException`
- 对比 Web UI 请求，发现前端传了 `scheduleTime=""`

---

### 发现 2：startParams 必须是 JSON 字符串 ⭐⭐

**问题：** 自定义参数传递失败

**正确格式：**
```python
# ✅ 正确
startParams = '{"dt": "2026-03-17"}'

# ❌ 错误
startParams = {'dt': '2026-03-17'}
startParams = 'dt=2026-03-17'
```

**PowerShell 转换：**
```powershell
$startParamsJsonStr = @{ "dt" = "2026-03-17" } | ConvertTo-Json -Compress
```

**Python 转换：**
```python
import json
startParams = json.dumps({"dt": "2026-03-17"})
```

---

### 发现 3：tenantCode 影响权限校验 ⭐⭐

**问题：** 即使用户是 ADMIN_USER，API 调用仍可能失败

**根因：** 后端默认使用 `tenantCode="default"`，但用户实际租户是 `dolphinscheduler`

**解决方案：**
```python
body['tenantCode'] = "dolphinscheduler"  # 显式指定租户
```

---

### 发现 4：taskDependType 控制执行范围 ⭐⭐⭐

**三种模式：**

| 模式 | 执行范围 | 使用场景 |
|------|----------|----------|
| `TASK_ONLY` | 只执行指定任务 | 🎯 单独重跑某个任务 |
| `TASK_POST` | 指定任务 + 所有下游 | 正常启动（默认） |
| `TASK_PRE` | 指定任务 + 所有上游 | 补修数据链路 |

**示例：**
```python
# 只执行单个任务
body['taskDependType'] = "TASK_ONLY"
body['startNodeList'] = "168251685969600"

# 执行整个工作流
body['taskDependType'] = "TASK_POST"
# 不传 startNodeList
```

---

## 🚀 完整代码

### Python 版本

```python
#!/usr/bin/env python3
import requests
import json

def start_workflow(project_code, process_code, dt=None, task_code=None, task_depend_type="TASK_POST"):
    """
    启动 DolphinScheduler 工作流
    
    Args:
        project_code: 项目 Code
        process_code: 工作流 Code
        dt: 业务日期（可选）
        task_code: 任务 Code（可选，指定单个任务时使用）
        task_depend_type: 任务依赖类型（TASK_ONLY/TASK_POST/TASK_PRE）
    
    Returns:
        响应字典
    """
    base_url = "http://127.0.0.1:12345/dolphinscheduler"
    token = "0cad23ded0f0e942381fc9717c1581a8"
    
    headers = {
        'token': token,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    body = {
        'processDefinitionCode': process_code,
        'failureStrategy': 'CONTINUE',
        'warningType': 'NONE',
        'warningGroupId': '0',
        'processInstancePriority': 'MEDIUM',
        'workerGroup': 'default',
        'environmentCode': '154818922491872',  # prod
        'tenantCode': 'dolphinscheduler',
        'taskDependType': task_depend_type,
        'runMode': 'RUN_MODE_SERIAL',
        'execType': 'START_PROCESS',
        'dryRun': '0',
        'scheduleTime': '',  # ⚠️ 必须传空字符串！
    }
    
    # 添加自定义参数
    if dt:
        body['startParams'] = json.dumps({"dt": dt})
    
    # 添加任务 Code（指定单个任务时）
    if task_code:
        body['startNodeList'] = task_code
    
    url = f"{base_url}/projects/{project_code}/executors/start-process-instance"
    response = requests.post(url, headers=headers, data=body, timeout=30)
    
    return response.json()

# 使用示例
if __name__ == '__main__':
    # 场景 1：执行整个工作流
    result = start_workflow(
        project_code="159737550740160",
        process_code="168243093291713",
        dt="2026-03-17"
    )
    print(f"实例 ID: {result.get('data')}")
    
    # 场景 2：只执行单个任务
    result = start_workflow(
        project_code="159737550740160",
        process_code="168243093291713",
        dt="2026-03-17",
        task_code="168251685969600",
        task_depend_type="TASK_ONLY"
    )
    print(f"实例 ID: {result.get('data')}")
```

---

### PowerShell 版本

```powershell
# 启动工作流函数
function Start-DolphinWorkflow {
    param(
        [string]$ProjectCode,
        [string]$ProcessCode,
        [string]$Dt,
        [string]$TaskCode,
        [string]$TaskDependType = "TASK_POST"
    )
    
    $token = "0cad23ded0f0e942381fc9717c1581a8"
    $uri = "http://127.0.0.1:12345/dolphinscheduler/projects/$ProjectCode/executors/start-process-instance"
    
    # 自定义参数转换为 JSON 字符串
    $startParams = @{}
    if ($Dt) { $startParams['dt'] = $Dt }
    $startParamsJson = $startParams | ConvertTo-Json -Compress
    
    # 构建请求体
    $body = @{
        "processDefinitionCode" = $ProcessCode
        "failureStrategy" = "CONTINUE"
        "warningType" = "NONE"
        "warningGroupId" = "0"
        "processInstancePriority" = "MEDIUM"
        "workerGroup" = "default"
        "environmentCode" = "154818922491872"
        "tenantCode" = "dolphinscheduler"
        "taskDependType" = $TaskDependType
        "runMode" = "RUN_MODE_SERIAL"
        "execType" = "START_PROCESS"
        "dryRun" = "0"
        "scheduleTime" = ""  # ⚠️ 必须传！
        "startParams" = $startParamsJson
    }
    
    # 添加任务 Code
    if ($TaskCode) {
        $body['startNodeList'] = $TaskCode
    }
    
    # 发送请求
    $headers = @{ "token" = $token }
    $response = Invoke-RestMethod -Uri $uri -Method POST -Headers $headers -Body $body
    
    return $response
}

# 使用示例
# 场景 1：执行整个工作流
Start-DolphinWorkflow -ProjectCode "159737550740160" -ProcessCode "168243093291713" -Dt "2026-03-17"

# 场景 2：只执行单个任务
Start-DolphinWorkflow -ProjectCode "159737550740160" -ProcessCode "168243093291713" -TaskCode "168251685969600" -TaskDependType "TASK_ONLY" -Dt "2026-03-17"
```

---

## 📖 使用场景

### 场景 1：基础启动（无自定义参数）

**需求：** 启动工作流，使用默认参数

**代码：**
```python
result = start_workflow(
    project_code="159737550740160",
    process_code="168243093291713"
)
```

**响应：**
```json
{
    "code": 0,
    "msg": "success",
    "data": 168250925189824
}
```

---

### 场景 2：带业务日期启动

**需求：** 传递 `dt=2026-03-17` 给工作流

**代码：**
```python
result = start_workflow(
    project_code="159737550740160",
    process_code="168243093291713",
    dt="2026-03-17"
)
```

**参数优先级：**
启动参数 > 局部参数 > 上游传递 > 全局参数 > 项目参数

---

### 场景 3：只执行单个任务

**需求：** 只执行 `market_fee_by_channel_2` 任务

**代码：**
```python
result = start_workflow(
    project_code="159737550740160",
    process_code="168243093291713",
    task_code="168251685969600",
    task_depend_type="TASK_ONLY",
    dt="2026-03-17"
)
```

**查询任务 Code：**
```python
import requests

url = "http://127.0.0.1:12345/dolphinscheduler/projects/159737550740160/process-definition/168243093291713"
headers = {'token': '0cad23ded0f0e942381fc9717c1581a8'}
response = requests.get(url, headers=headers)

tasks = response.json()['data']['taskDefinitionList']
for task in tasks:
    print(f"任务：{task['name']} | Code: {task['code']}")
```

---

### 场景 4：执行当前 + 所有下游

**需求：** 执行指定任务及其所有下游任务

**代码：**
```python
result = start_workflow(
    project_code="159737550740160",
    process_code="168243093291713",
    task_code="168251685969600",
    task_depend_type="TASK_POST"
)
```

---

### 场景 5：执行当前 + 所有上游

**需求：** 执行指定任务及其所有上游任务（补修数据）

**代码：**
```python
result = start_workflow(
    project_code="159737550740160",
    process_code="168243093291713",
    task_code="168251685969600",
    task_depend_type="TASK_PRE"
)
```

---

## 🔍 调试过程

### 第 1 步：基础尝试（失败）

```python
body = {
    'processDefinitionCode': '168243093291713'
}
# ❌ 错误 50014
```

**问题：** 参数太少

---

### 第 2 步：添加必填参数（失败）

```python
body = {
    'processDefinitionCode': '168243093291713',
    'failureStrategy': 'CONTINUE',
    'warningType': 'NONE',
    'environmentCode': '154818922491872'
}
# ❌ 错误 50014
```

**问题：** 还是缺少参数

---

### 第 3 步：添加 tenantCode（失败）

```python
body = {
    # ... 其他参数 ...
    'tenantCode': 'dolphinscheduler'
}
# ❌ 错误 50014
```

**问题：** 仍然失败

---

### 第 4 步：查看服务端日志（突破）

**日志关键信息：**
```
MissingServletRequestParameterException: 
Required request parameter 'scheduleTime' for method parameter type String is not present
```

**发现：** `scheduleTime` 是必填参数！

---

### 第 5 步：添加 scheduleTime（成功）

```python
body = {
    # ... 其他参数 ...
    'scheduleTime': ''  # 空字符串即可
}
# ✅ 成功！
```

**响应：**
```json
{"code": 0, "msg": "success", "data": 168250925189824}
```

---

## ⚠️ 常见错误

### 错误 50014：启动工作流实例错误

**最常见原因：**

| 原因 | 解决方案 | 优先级 |
|------|----------|--------|
| 缺少 `scheduleTime` | 添加 `"scheduleTime": ""` | ⭐⭐⭐⭐⭐ |
| 环境 Code 不存在 | 检查 environmentCode | ⭐⭐⭐⭐ |
| 租户 Code 错误 | 添加 tenantCode | ⭐⭐⭐⭐ |
| 工作流未发布 | 确认状态为 ONLINE | ⭐⭐⭐ |

**排查步骤：**
```python
# 1. 查询工作流状态
info = get_workflow_info(project_code, process_code)
print(info['data']['processDefinition']['releaseState'])  # 应该是 ONLINE

# 2. 查询任务环境配置
env_code = info['data']['taskDefinitionList'][0]['environmentCode']
print(f"任务环境 Code: {env_code}")

# 3. 查询可用环境列表
envs = get_environments()
print(f"可用环境：{[e['code'] for e in envs['data']]}")
```

---

### 错误 1200009：环境配置不存在

**原因：** 任务使用的环境 Code 无效

**解决方案：**
1. 查询可用环境：`get_environments()`
2. 在 Web UI 修改工作流任务的环境配置
3. 重新发布工作流

---

### 错误 10109：查询工作流详情错误

**原因：** 项目 Code 或工作流 Code 错误

**解决方案：** 确认 Code 值正确

---

## 📊 最佳实践

### 1. 参数校验

```python
def validate_params(project_code, process_code):
    """校验参数是否有效"""
    # 检查项目是否存在
    # 检查工作流是否存在
    # 检查工作流是否已发布
    pass
```

---

### 2. 错误重试

```python
import time

def start_with_retry(project_code, process_code, max_retries=3):
    """带重试的启动"""
    for i in range(max_retries):
        result = start_workflow(project_code, process_code)
        if result['code'] == 0:
            return result
        time.sleep(2 ** i)  # 指数退避
    return result
```

---

### 3. 日志记录

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_workflow(project_code, process_code, **kwargs):
    logger.info(f"启动工作流：{project_code}/{process_code}")
    result = _start_workflow_impl(project_code, process_code, **kwargs)
    if result['code'] == 0:
        logger.info(f"启动成功，实例 ID: {result['data']}")
    else:
        logger.error(f"启动失败：{result['msg']}")
    return result
```

---

### 4. 配置管理

```python
# config.py
CONFIG = {
    'base_url': 'http://127.0.0.1:12345/dolphinscheduler',
    'token': '0cad23ded0f0e942381fc9717c1581a8',
    'environment_code': '154818922491872',
    'tenant_code': 'dolphinscheduler',
}

# 使用时
from config import CONFIG
```

---

## 📁 相关文件

| 文件名 | 说明 |
|--------|------|
| `dolphinscheduler_api.py` | Python API 脚本 |
| `DOLPHINSCHEDULER_USAGE.md` | 使用指南 |
| `DOLPHINSCHEDULER_EXAMPLES.md` | 调用示例大全 |
| `dolphinscheduler-api-complete-guide.md` | PowerShell 完整指南 |

---

## 🔗 参考链接

- [DolphinScheduler 官方文档](https://dolphinscheduler.apache.org/)
- [OpenClaw 文档](https://docs.openclaw.ai/)
- [ClawHub 技能市场](https://clawhub.ai/)

---

## 📝 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2026-03-17 | 初始版本，包含完整实践记录 |

---

**最后更新：** 2026-03-17 17:40 GMT+8

**作者：** 陈江川

**审核：** OpenClaw 社区
