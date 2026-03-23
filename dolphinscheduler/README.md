# DolphinScheduler 调度模块

> 通过 API 自动化控制 DolphinScheduler 工作流

---

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `dolphinscheduler_api.py` | 主 API 脚本，包含完整客户端类 |
| `dolphinscheduler-workflows.csv` | 工作流配置数据 |
| `examples/` | 使用示例代码 |

---

## 🚀 快速开始

### 基础启动

```python
from dolphinscheduler_api import start_workflow_simple

result = start_workflow_simple(
    project_code="159737550740160",
    process_code="168243093291713"
)
```

### 带参数启动

```python
result = start_workflow_simple(
    "159737550740160",
    "168243093291713",
    dt="2026-03-17",
    channel="app"
)
```

### 单任务执行

```python
from dolphinscheduler_api import start_single_task

result = start_single_task(
    "159737550740160",
    "168243093291713",
    "168251685969600",  # 任务 Code
    dt="2026-03-17"
)
```

---

## 🔧 配置说明

默认配置：
```python
{
    'base_url': 'http://127.0.0.1:12345/dolphinscheduler',
    'token': '你的Token',
    'environment_code': '154818922491872',  # prod
    'tenant_code': 'dolphinscheduler'
}
```

---

## 📖 详细文档

详见 [../docs/dolphinscheduler-api-guide.md](../docs/dolphinscheduler-api-guide.md)

---

**最后更新：** 2026-03-23
