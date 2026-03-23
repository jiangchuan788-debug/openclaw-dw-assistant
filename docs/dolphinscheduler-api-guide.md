# DolphinScheduler API 完全指南

> **一站式 DolphinScheduler API 调用指南**  
> **作者：** 陈江川  
> **日期：** 2026-03-17  
> **版本：** v2.0（合并版）  
> **适用对象：** OpenClaw 用户、DolphinScheduler 开发者

---

## 📋 目录

1. [快速开始](#快速开始)
2. [环境信息](#环境信息)
3. [核心发现](#核心发现)
4. [API 使用指南](#api-使用指南)
5. [场景示例](#场景示例)
6. [告警集成](#告警集成)
7. [附录](#附录)

---

## 快速开始

### 30 秒启动工作流

```python
from dolphinscheduler.dolphinscheduler_api import start_workflow_simple

# 基础启动
result = start_workflow_simple(
    project_code="159737550740160",
    process_code="168243093291713"
)

print(f"✅ 实例 ID: {result['instance_id']}")
```

### 带业务日期启动

```python
result = start_workflow_simple(
    "159737550740160",
    "168243093291713",
    dt="2026-03-17"
)
```

### 只执行单个任务

```python
from dolphinscheduler.dolphinscheduler_api import start_single_task

result = start_single_task(
    "159737550740160",
    "168243093291713",
    "168251685969600",  # 任务 Code
    dt="2026-03-17"
)
```

---

## 环境信息

### API 端点

| 配置项 | 值 |
|--------|-----|
| API 地址 | `http://172.20.0.235:12345/dolphinscheduler`（内网映射） |
| Token | `0cad23ded0f0e942381fc9717c1581a8` |
| 用户 | jiangchuanchen (ADMIN_USER) |
| 租户 | dolphinscheduler |

### 项目 Code

| 项目名称 | 项目 Code |
|----------|-----------|
| okr_ads | 159737550740160 |
| 国内数仓 - 工作流 | 158514956085248 |

### 环境 Code

| 环境 | Code |
|------|------|
| prod | 154818922491872 |
| develop | 154818735899616 |
| global | 154818709784544 |

---

## 核心发现

### 发现 1：scheduleTime 是必填参数 ⭐⭐⭐

**问题：** API 调用返回 50014 错误  
**根因：** Spring Boot 强制校验 `scheduleTime` 参数  
**解决：**
```python
body['scheduleTime'] = ""  # 必须传空字符串！
```

### 发现 2：startParams 必须是 JSON 字符串 ⭐⭐

```python
# ✅ 正确
startParams = json.dumps({"dt": "2026-03-17"})

# ❌ 错误
startParams = {'dt': '2026-03-17'}  # 字典不行
```

### 发现 3：tenantCode 影响权限校验 ⭐⭐

```python
body['tenantCode'] = "dolphinscheduler"  # 显式指定租户
```

### 发现 4：taskDependType 控制执行范围 ⭐⭐⭐

| 模式 | 执行范围 |
|------|----------|
| `TASK_ONLY` | 只执行指定任务 |
| `TASK_POST` | 当前 + 所有下游（默认） |
| `TASK_PRE` | 当前 + 所有上游 |

---

## API 使用指南

### 完整代码示例

```python
from dolphinscheduler.dolphinscheduler_api import DolphinSchedulerClient

# 创建客户端
client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

# 启动工作流
result = client.start_workflow(
    project_code="159737550740160",
    process_code="168243093291713",
    custom_params={"dt": "2026-03-17"}
)

if result['success']:
    print(f"✅ 实例 ID: {result['instance_id']}")
```

### 命令行调用

```bash
# 基础启动
python dolphinscheduler/dolphinscheduler_api.py \
    --project 159737550740160 \
    --process 168243093291713

# 带业务日期
python dolphinscheduler/dolphinscheduler_api.py \
    --project 159737550740160 \
    --process 168243093291713 \
    --dt 2026-03-17

# 只执行单个任务
python dolphinscheduler/dolphinscheduler_api.py \
    --project 159737550740160 \
    --process 168243093291713 \
    --task 168251685969600 \
    --mode single \
    --dt 2026-03-17
```

---

## 场景示例

### 场景 1：基础启动

```python
result = start_workflow_simple(
    project_code="159737550740160",
    process_code="168243093291713"
)
```

### 场景 2：带业务日期

```python
result = start_workflow_simple(
    "159737550740160",
    "168243093291713",
    dt="2026-03-17"
)
```

### 场景 3：只执行单个任务

```python
result = start_workflow_simple(
    "159737550740160",
    "168243093291713",
    task_code="168251685969600",
    task_depend_type="TASK_ONLY",
    dt="2026-03-17"
)
```

### 场景 4：批量启动多个工作流

```python
from concurrent.futures import ThreadPoolExecutor

workflows = [
    {"project": "159737550740160", "process": "168243093291713"},
    {"project": "159737550740160", "process": "161520882085569"},
]

def start_single(wf):
    return client.start_workflow(
        project_code=wf['project'],
        process_code=wf['process'],
        custom_params={"dt": "2026-03-17"}
    )

with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(start_single, workflows))
```

### 场景 5：定时调度

```python
import schedule
import time

def daily_etl():
    result = start_workflow_simple(
        "159737550740160",
        "168243093291713",
        dt=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    )
    print(f"ETL 结果: {result}")

schedule.every().day.at("02:00").do(daily_etl)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 告警集成

本项目包含完整的告警自动化系统，详见 [alert/](../alert/) 目录。

**核心功能：**
- 数据库告警监控
- OpenClaw Webhook 通知
- 钉钉群消息推送
- 自动状态回写

**快速链接：**
- [告警系统说明](../alert/README.md)
- [告警桥接脚本](../alert/alert_bridge.py)

---

## 附录

### 常见错误

| 错误码 | 原因 | 解决方案 |
|--------|------|----------|
| 50014 | 缺少 scheduleTime | 添加 `"scheduleTime": ""` |
| 1200009 | 环境配置不存在 | 检查 environmentCode |
| 10109 | 工作流 Code 错误 | 确认 Code 值正确 |

### 参数表

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_code | str | ✅ | 项目 Code |
| process_code | str | ✅ | 工作流 Code |
| custom_params | dict | ❌ | 自定义参数 |
| task_code | str | ❌ | 任务 Code |
| task_depend_type | str | ❌ | TASK_ONLY/POST/PRE |

### 相关文件

| 文件 | 说明 |
|------|------|
| `dolphinscheduler_api.py` | Python API 主模块 |
| `dolphinscheduler-workflows.csv` | 工作流数据 |
| `examples/` | 使用示例 |

---

**最后更新：** 2026-03-23  
**维护者：** 陈江川
