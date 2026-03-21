# DolphinScheduler API 调用示例大全

> **完整场景覆盖** - 从基础到高级的所有使用方式  
> **更新日期：** 2026-03-17

---

## 📋 目录

1. [基础调用](#基础调用)
2. [自定义参数](#自定义参数)
3. [单任务执行](#单任务执行)
4. [任务依赖模式](#任务依赖模式)
5. [查询操作](#查询操作)
6. [命令行调用](#命令行调用)
7. [集成示例](#集成示例)

---

## 🚀 基础调用

### 示例 1：最简启动

```python
from dolphinscheduler_api import start_workflow_simple

result = start_workflow_simple(
    project_code="159737550740160",
    process_code="168243093291713"
)

print(result)
# 输出：{'success': True, 'instance_id': 168250925189824, ...}
```

---

### 示例 2：使用客户端类

```python
from dolphinscheduler_api import DolphinSchedulerClient

# 创建客户端
client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

# 启动工作流
result = client.start_workflow(
    project_code="159737550740160",
    process_code="168243093291713"
)

if result['success']:
    print(f"✅ 实例 ID: {result['instance_id']}")
else:
    print(f"❌ {result['error_message']}")
```

---

## 🎯 自定义参数

### 示例 3：传递业务日期

```python
from dolphinscheduler_api import start_workflow_simple

result = start_workflow_simple(
    project_code="159737550740160",
    process_code="168243093291713",
    dt="2026-03-17"
)
```

---

### 示例 4：传递多个参数

```python
from dolphinscheduler_api import DolphinSchedulerClient

client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

result = client.start_workflow(
    project_code="159737550740160",
    process_code="168243093291713",
    custom_params={
        "dt": "2026-03-17",
        "channel": "app",
        "is_test": "1",
        "batch_id": "20260317001"
    }
)
```

---

### 示例 5：动态生成日期

```python
from dolphinscheduler_api import start_workflow_simple
from datetime import datetime, timedelta

# 昨天的日期
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

result = start_workflow_simple(
    project_code="159737550740160",
    process_code="168243093291713",
    dt=yesterday  # dt="2026-03-16"
)
```

---

## 🎯 单任务执行

### 示例 6：只执行一个任务

```python
from dolphinscheduler_api import start_single_task

result = start_single_task(
    project_code="159737550740160",
    process_code="168243093291713",
    task_code="168251685969600",  # market_fee_by_channel_2
    dt="2026-03-17"
)

if result['success']:
    print(f"✅ 只执行了单个任务，实例 ID: {result['instance_id']}")
```

---

### 示例 7：查询任务 Code 后执行

```python
from dolphinscheduler_api import DolphinSchedulerClient

client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

# 1. 查询工作流详情
info = client.get_workflow_info("159737550740160", "168243093291713")

if info['success']:
    tasks = info['data'].get('taskDefinitionList', [])
    
    # 2. 找到目标任务
    target_task = None
    for task in tasks:
        if task['name'] == 'market_fee_by_channel_2':
            target_task = task
            break
    
    if target_task:
        # 3. 启动单个任务
        result = client.start_workflow(
            project_code="159737550740160",
            process_code="168243093291713",
            task_code=str(target_task['code']),
            task_depend_type="TASK_ONLY",
            custom_params={"dt": "2026-03-17"}
        )
        
        if result['success']:
            print(f"✅ 启动成功！实例 ID: {result['instance_id']}")
```

---

## 🔗 任务依赖模式

### 示例 8：执行当前 + 所有下游

```python
from dolphinscheduler_api import DolphinSchedulerClient

client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

result = client.start_workflow(
    project_code="159737550740160",
    process_code="168243093291713",
    task_code="168251685969600",
    task_depend_type="TASK_POST"  # 执行当前 + 所有下游
)
```

---

### 示例 9：执行当前 + 所有上游

```python
from dolphinscheduler_api import DolphinSchedulerClient

client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

result = client.start_workflow(
    project_code="159737550740160",
    process_code="168243093291713",
    task_code="168251685969600",
    task_depend_type="TASK_PRE"  # 执行当前 + 所有上游
)
```

---

### 示例 10：同时启动多个任务

```python
from dolphinscheduler_api import DolphinSchedulerClient

client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

# 同时启动两个任务作为起点
result = client.start_workflow(
    project_code="159737550740160",
    process_code="168243093291713",
    task_code="168251685969600,168243093291712",  # 多个任务用逗号分隔
    task_depend_type="TASK_POST"
)
```

---

## 🔍 查询操作

### 示例 11：查询工作流列表

```python
from dolphinscheduler_api import DolphinSchedulerClient

client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

# 查询项目下所有工作流
result = client.get_workflows_list("159737550740160")

if result['success']:
    print(f"{'工作流名称':<50} {'Code':<20} {'版本':<10}")
    print("-" * 80)
    for workflow in result['data']:
        print(f"{workflow['name']:<50} {workflow['code']:<20} {workflow['version']:<10}")
```

---

### 示例 12：查询环境列表

```python
from dolphinscheduler_api import DolphinSchedulerClient

client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

# 查询可用环境
result = client.get_environments()

if result['success']:
    print(f"{'环境名称':<20} {'环境 Code':<20}")
    print("-" * 40)
    for env in result['data']:
        print(f"{env['name']:<20} {env['code']:<20}")
```

---

### 示例 13：查询用户信息

```python
from dolphinscheduler_api import DolphinSchedulerClient

client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

# 查询当前用户
result = client.get_user_info()

if result['success']:
    user = result['data']
    print(f"用户名：{user['userName']}")
    print(f"用户 ID: {user['id']}")
    print(f"用户类型：{user['userType']}")
    print(f"租户：{user['tenantCode']}")
```

---

## 💻 命令行调用

### 示例 14：基础启动

```bash
python dolphinscheduler_api.py \
    --project 159737550740160 \
    --process 168243093291713
```

---

### 示例 15：带业务日期

```bash
python dolphinscheduler_api.py \
    --project 159737550740160 \
    --process 168243093291713 \
    --dt 2026-03-17
```

---

### 示例 16：只执行单个任务

```bash
python dolphinscheduler_api.py \
    --project 159737550740160 \
    --process 168243093291713 \
    --task 168251685969600 \
    --mode single \
    --dt 2026-03-17
```

---

### 示例 17：执行当前 + 下游

```bash
python dolphinscheduler_api.py \
    --project 159737550740160 \
    --process 168243093291713 \
    --task 168251685969600 \
    --mode post
```

---

### 示例 18：执行当前 + 上游

```bash
python dolphinscheduler_api.py \
    --project 159737550740160 \
    --process 168243093291713 \
    --task 168251685969600 \
    --mode pre
```

---

## 🔗 集成示例

### 示例 19：定时任务调度

```python
# schedule_workflow.py
from dolphinscheduler_api import start_workflow_simple
from datetime import datetime, timedelta
import schedule
import time

def daily_etl_job():
    """每日 ETL 任务"""
    # 计算昨天的日期
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"[{datetime.now()}] 启动每日 ETL 任务，dt={yesterday}")
    
    result = start_workflow_simple(
        project_code="159737550740160",
        process_code="168243093291713",
        dt=yesterday
    )
    
    if result['success']:
        print(f"✅ ETL 任务启动成功，实例 ID: {result['instance_id']}")
    else:
        print(f"❌ ETL 任务启动失败：{result['error_message']}")

# 每天早上 2 点执行
schedule.every().day.at("02:00").do(daily_etl_job)

print("调度器已启动...")
while True:
    schedule.run_pending()
    time.sleep(60)
```

---

### 示例 20：工作流监控脚本

```python
# monitor_workflow.py
from dolphinscheduler_api import DolphinSchedulerClient
import time

client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

def wait_for_completion(instance_id, timeout=3600):
    """等待工作流实例完成"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # 查询实例状态（需要实现 get_instance_status 方法）
        # status = client.get_instance_status(instance_id)
        
        # if status == 'SUCCESS':
        #     print("✅ 工作流执行成功")
        #     return True
        # elif status == 'FAILURE':
        #     print("❌ 工作流执行失败")
        #     return False
        
        time.sleep(60)
    
    print("⏰ 等待超时")
    return False

# 启动工作流
result = client.start_workflow(
    project_code="159737550740160",
    process_code="168243093291713",
    custom_params={"dt": "2026-03-17"}
)

if result['success']:
    instance_id = result['instance_id']
    print(f"工作流已启动，实例 ID: {instance_id}")
    
    # 等待完成
    wait_for_completion(instance_id)
```

---

### 示例 21：批量启动多个工作流

```python
# batch_start.py
from dolphinscheduler_api import DolphinSchedulerClient
from concurrent.futures import ThreadPoolExecutor

client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

workflows = [
    {"project": "159737550740160", "process": "168243093291713"},
    {"project": "159737550740160", "process": "161520882085569"},
    {"project": "159737550740160", "process": "161521065974465"},
]

def start_single_workflow(workflow_info):
    """启动单个工作流"""
    result = client.start_workflow(
        project_code=workflow_info['project'],
        process_code=workflow_info['process'],
        custom_params={"dt": "2026-03-17"}
    )
    
    return {
        'project': workflow_info['project'],
        'process': workflow_info['process'],
        'result': result
    }

# 并发启动所有工作流
with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(start_single_workflow, workflows))

# 输出结果
for r in results:
    if r['result']['success']:
        print(f"✅ {r['process']}: {r['result']['instance_id']}")
    else:
        print(f"❌ {r['process']}: {r['result']['error_message']}")
```

---

## 📊 完整参数说明

### start_workflow 参数表

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| project_code | str | ✅ | - | 项目 Code |
| process_code | str | ✅ | - | 工作流 Code |
| custom_params | dict | ❌ | None | 自定义参数字典 |
| task_code | str | ❌ | None | 任务 Code（单任务执行时用） |
| task_depend_type | str | ❌ | TASK_POST | 任务依赖类型 |
| environment_code | str | ❌ | prod | 环境 Code |
| tenant_code | str | ❌ | dolphinscheduler | 租户 Code |
| schedule_time | str | ✅ | "" | 调度时间（必须传空字符串） |

### task_depend_type 可选值

| 值 | 说明 | 使用场景 |
|----|------|----------|
| `TASK_ONLY` | 只执行指定任务 | 单独重跑某个任务 |
| `TASK_POST` | 执行当前 + 所有下游 | 正常启动（默认） |
| `TASK_PRE` | 执行当前 + 所有上游 | 补修数据链路 |

---

## 🔗 相关文档

- `dolphinscheduler_api.py` - Python 脚本
- `DOLPHINSCHEDULER_USAGE.md` - 使用指南
- `dolphinscheduler-api-complete-guide.md` - PowerShell 完整指南

---

**最后更新：** 2026-03-17 17:18 GMT+8
