# DolphinScheduler API 使用指南

> **版本：** v1.0  
> **更新日期：** 2026-03-17  
> **适用环境：** http://127.0.0.1:12345

---

## 📋 目录

1. [快速开始](#快速开始)
2. [环境准备](#环境准备)
3. [配置说明](#配置说明)
4. [使用场景](#使用场景)
5. [常见问题](#常见问题)

---

## 🚀 快速开始

### 30 秒启动工作流

```python
from dolphinscheduler_api import start_workflow_simple

# 基础启动
result = start_workflow_simple("159737550740160", "168243093291713")

if result['success']:
    print(f"✅ 启动成功！实例 ID: {result['instance_id']}")
else:
    print(f"❌ 失败：{result['error_message']}")
```

### 带业务日期启动

```python
from dolphinscheduler_api import start_workflow_simple

# 传递 dt 参数
result = start_workflow_simple(
    "159737550740160", 
    "168243093291713",
    dt="2026-03-17"
)

if result['success']:
    print(f"✅ 启动成功！实例 ID: {result['instance_id']}")
```

### 只执行单个任务

```python
from dolphinscheduler_api import start_single_task

# 只执行 market_fee_by_channel_2 任务
result = start_single_task(
    "159737550740160",
    "168243093291713",
    "168251685969600",  # 任务 Code
    dt="2026-03-17"
)

if result['success']:
    print(f"✅ 启动成功！实例 ID: {result['instance_id']}")
```

---

## 🛠️ 环境准备

### 1. 安装依赖

```bash
pip install requests
```

### 2. 获取 Token

1. 登录 DolphinScheduler Web UI
2. 点击 **安全中心** → **令牌管理**
3. 点击 **创建令牌**
4. 设置失效时间和用户
5. 拷贝 Token 字符串

**当前 Token：** `0cad23ded0f0e942381fc9717c1581a8`

### 3. 下载脚本

将 `dolphinscheduler_api.py` 放到项目目录

---

## ⚙️ 配置说明

### 方式 1：修改脚本默认配置（推荐）

编辑 `dolphinscheduler_api.py` 中的默认配置：

```python
# 在 DolphinSchedulerClient.__init__ 中
self.default_config = {
    'environment_code': '154818922491872',  # prod 环境
    'tenant_code': 'dolphinscheduler',
    'worker_group': 'default',
    # ... 其他配置
}
```

### 方式 2：调用时指定配置

```python
from dolphinscheduler_api import DolphinSchedulerClient

client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

# 调用时指定环境
result = client.start_workflow(
    project_code="159737550740160",
    process_code="168243093291713",
    environment_code="154818735899616"  # develop 环境
)
```

### 方式 3：使用配置文件

创建 `config.json`：

```json
{
    "base_url": "http://127.0.0.1:12345/dolphinscheduler",
    "token": "0cad23ded0f0e942381fc9717c1581a8",
    "default_environment_code": "154818922491872",
    "default_tenant_code": "dolphinscheduler"
}
```

---

## 📖 使用场景

### 场景 1：基础启动（无自定义参数）

```python
from dolphinscheduler_api import start_workflow_simple

result = start_workflow_simple(
    project_code="159737550740160",
    process_code="168243093291713"
)

if result['success']:
    print(f"✅ 实例 ID: {result['instance_id']}")
else:
    print(f"❌ {result['error_message']}")
```

---

### 场景 2：带自定义参数启动

```python
from dolphinscheduler_api import start_workflow_simple

# 传递业务日期
result = start_workflow_simple(
    project_code="159737550740160",
    process_code="168243093291713",
    dt="2026-03-17"
)
```

**传递多个参数：**

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
        "is_test": "1"
    }
)
```

---

### 场景 3：只执行单个任务

```python
from dolphinscheduler_api import start_single_task

# 只执行 market_fee_by_channel_2 任务
result = start_single_task(
    project_code="159737550740160",
    process_code="168243093291713",
    task_code="168251685969600",
    dt="2026-03-17"
)
```

**查询任务 Code：**

```python
from dolphinscheduler_api import DolphinSchedulerClient

client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

# 查询工作流详情
info = client.get_workflow_info("159737550740160", "168243093291713")

if info['success']:
    tasks = info['data'].get('taskDefinitionList', [])
    for task in tasks:
        print(f"任务：{task['name']} | Code: {task['code']}")
```

---

### 场景 4：执行当前任务 + 所有下游

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

### 场景 5：执行当前任务 + 所有上游

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

### 场景 6：命令行调用

```bash
# 基础启动
python dolphinscheduler_api.py --project 159737550740160 --process 168243093291713

# 带业务日期
python dolphinscheduler_api.py --project 159737550740160 --process 168243093291713 --dt 2026-03-17

# 只执行单个任务
python dolphinscheduler_api.py --project 159737550740160 --process 168243093291713 --task 168251685969600 --mode single --dt 2026-03-17

# 执行当前 + 下游
python dolphinscheduler_api.py --project 159737550740160 --process 168243093291713 --task 168251685969600 --mode post

# 执行当前 + 上游
python dolphinscheduler_api.py --project 159737550740160 --process 168243093291713 --task 168251685969600 --mode pre
```

---

### 场景 7：查询工作流列表

```python
from dolphinscheduler_api import DolphinSchedulerClient

client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

# 查询项目下所有工作流
result = client.get_workflows_list("159737550740160")

if result['success']:
    for workflow in result['data']:
        print(f"工作流：{workflow['name']} | Code: {workflow['code']} | 版本：{workflow['version']}")
```

---

### 场景 8：查询环境列表

```python
from dolphinscheduler_api import DolphinSchedulerClient

client = DolphinSchedulerClient(
    base_url="http://127.0.0.1:12345/dolphinscheduler",
    token="0cad23ded0f0e942381fc9717c1581a8"
)

# 查询可用环境
result = client.get_environments()

if result['success']:
    for env in result['data']:
        print(f"环境：{env['name']} | Code: {env['code']}")
```

---

## ⚠️ 常见问题

### 错误 50014：启动工作流实例错误

**最常见原因：** 缺少 `scheduleTime` 参数

**解决方案：** 确保调用时传递 `scheduleTime=""`（空字符串）

```python
# ✅ 正确
result = client.start_workflow(
    project_code="...",
    process_code="...",
    schedule_time=""  # 必须传！
)
```

### 错误 1200009：环境配置不存在

**原因：** 任务使用的环境 Code 无效

**解决方案：**
1. 查询可用环境：`client.get_environments()`
2. 在 Web UI 中修改工作流任务的环境配置
3. 重新发布工作流

### 错误 10109：查询工作流详情错误

**原因：** 项目 Code 或工作流 Code 错误

**解决方案：** 确认 Code 值正确

---

## 📊 快速参考表

### 项目 Code

| 项目名称 | 项目 Code |
|----------|-----------|
| okr_ads | 159737550740160 |
| 国内数仓 - 工作流 | 158514956085248 |

### 环境 Code

| 环境名称 | 环境 Code |
|----------|-----------|
| prod | 154818922491872 |
| develop | 154818735899616 |
| global | 154818709784544 |

### task_depend_type 模式

| 模式 | 说明 | 使用场景 |
|------|------|----------|
| `TASK_ONLY` | 只执行指定任务 | 🎯 单独重跑某个任务 |
| `TASK_POST` | 执行当前 + 所有下游 | 正常启动（默认） |
| `TASK_PRE` | 执行当前 + 所有上游 | 补修数据链路 |

---

## 🔗 相关文档

- `dolphinscheduler_api.py` - Python 脚本
- `dolphinscheduler-api-complete-guide.md` - PowerShell 完整指南
- `dolphinscheduler-start-error-report.md` - 启动失败报告

---

**最后更新：** 2026-03-17 17:18 GMT+8
