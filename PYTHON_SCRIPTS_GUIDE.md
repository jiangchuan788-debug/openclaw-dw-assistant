# Python 脚本清单

本文档梳理 `openclaw-dw-assistant` 项目中所有 Python 脚本及其用途。

---

## 📁 DolphinScheduler 调度脚本 (`dolphinscheduler/`)

### 1. check_running.py
**用途**: 检测国内数仓-工作流项目中是否有正在运行的工作流实例

**功能**:
- 查询运行中的工作流实例（RUNNING_EXECUTION 状态）
- 显示工作流名称、实例ID、状态、开始时间、已运行时长
- 支持按名称筛选（模糊匹配）
- 支持只检查模式（返回退出码，方便脚本调用）

**使用示例**:
```bash
# 查看所有运行中的实例
python check_running.py

# 筛选特定名称
python check_running.py -f "同步"

# 只检查是否有运行中
python check_running.py --check-only
echo $?  # 0=空闲, 1=运行中
```

**关键输出**:
- 工作流名称和实例ID
- 工作流Code（用于API调用）
- 运行时长

---

### 2. list_workflows.py
**用途**: 查询国内数仓-工作流项目中的所有定时任务工作流（已上线的）

**功能**:
- 列出项目中的所有工作流定义
- 显示工作流名称、状态、版本、Code、更新时间
- 支持按名称筛选（模糊匹配）
- 支持按状态筛选（ONLINE/OFFLINE）
- 支持简洁模式（只显示名称和Code）

**使用示例**:
```bash
# 显示所有已上线工作流
python list_workflows.py

# 筛选每日调度（D-1）的工作流
python list_workflows.py -f "D-1"

# 显示最多100个工作流
python list_workflows.py -l 100

# 简洁模式（适合复制Code）
python list_workflows.py --list-codes

# 显示已下线的工作流
python list_workflows.py -s OFFLINE
```

**关键输出**:
- 工作流名称、状态、版本
- 工作流Code（processDefinitionCode）
- 更新时间

---

### 3. dolphinscheduler_api.py
**用途**: DolphinScheduler API 客户端和启动脚本

**功能**:
- 提供 `DolphinSchedulerClient` 类封装 API 调用
- 支持启动工作流（整个工作流或单个任务）
- 支持传递自定义参数（如业务日期 dt）
- 支持不同的任务依赖类型（TASK_ONLY/TASK_POST/TASK_PRE）
- 命令行接口（CLI）支持

**使用示例**:
```python
# Python API
from dolphinscheduler_api import start_workflow_simple

result = start_workflow_simple(
    project_code="159737550740160",
    process_code="168243093291713",
    dt="2026-03-23"
)
```

```bash
# 命令行
python dolphinscheduler_api.py \
  --project 159737550740160 \
  --process 168243093291713 \
  --dt 2026-03-23
```

**配置**:
- DS 地址: `http://172.20.0.235:12345/dolphinscheduler`
- Token: `0cad23ded0f0e942381fc9717c1581a8`

---

## 📁 告警系统脚本 (`alert/`)

### 4. alert_bridge.py
**用途**: 告警桥接主脚本（Python 版）

**功能**:
- 监控数据库中的未处理告警（status=0）
- 将告警格式化后发送给 OpenClaw Webhook
- 自动标记已处理的告警（status=1）
- 支持定时任务模式

**配置**:
- 数据库: `172.20.0.235:13306/wattrel`
- Webhook: `http://127.0.0.1:18789/hooks/wattrel/wake`

**使用示例**:
```bash
# 手动运行一次
python alert_bridge.py --once

# 持续监控（每30分钟）
python alert_bridge.py --interval 30
```

**注意**: 需要安装 `pymysql` 和 `requests` 库

---

### 5. test_db_connection.py
**用途**: 测试告警数据库连接和查询

**功能**:
- 测试数据库连接
- 查询告警统计（总计/未处理/已处理）
- 列出未处理告警详情

**使用示例**:
```bash
python test_db_connection.py
```

**输出**:
- 数据库连接状态
- 告警统计信息
- 未处理告警列表（最多10条）

---

### 6. send_alert.py
**用途**: 告警发送脚本

**功能**:
- 格式化告警消息
- 发送告警到 OpenClaw Webhook
- 支持钉钉消息格式

**使用场景**:
- 其他脚本调用此脚本发送告警
- 手动发送测试告警

---

### 7. check_alerts.py
**用途**: 简单的告警检查脚本

**功能**:
- 快速检查数据库中的告警数量
- 输出未处理告警数量

---

### 8. debug_alerts.py
**用途**: 告警调试工具

**功能**:
- 调试告警格式化
- 测试数据库连接
- 输出详细的告警字段信息

---

## 📊 脚本对比表

| 脚本 | 位置 | 主要功能 | 依赖 | 常用程度 |
|------|------|---------|------|---------|
| `check_running.py` | dolphinscheduler/ | 检测运行中的工作流 | 标准库 | ⭐⭐⭐⭐⭐ |
| `list_workflows.py` | dolphinscheduler/ | 列出所有工作流 | 标准库 | ⭐⭐⭐⭐⭐ |
| `dolphinscheduler_api.py` | dolphinscheduler/ | API客户端 | 标准库 | ⭐⭐⭐⭐ |
| `alert_bridge.py` | alert/ | 告警桥接 | pymysql, requests | ⭐⭐⭐ |
| `test_db_connection.py` | alert/ | 测试数据库连接 | pymysql | ⭐⭐ |
| `send_alert.py` | alert/ | 发送告警 | requests | ⭐⭐ |
| `check_alerts.py` | alert/ | 简单告警检查 | pymysql | ⭐ |
| `debug_alerts.py` | alert/ | 告警调试 | pymysql | ⭐ |

---

## 🚀 常用组合命令

### 日常监控
```bash
# 1. 检查是否有运行中的工作流
python dolphinscheduler/check_running.py --check-only

# 2. 查看运行中的工作流详情
python dolphinscheduler/check_running.py

# 3. 查看所有工作流列表
python dolphinscheduler/list_workflows.py
```

### 启动工作流前检查
```bash
# 检查是否空闲
if python dolphinscheduler/check_running.py --check-only; then
    echo "DS空闲，可以启动新任务"
    # 启动工作流...
else
    echo "DS忙碌，请等待"
fi
```

### 告警处理
```bash
# 测试告警数据库连接
python alert/test_db_connection.py

# 运行告警桥接
python alert/alert_bridge.py --once
```

---

## 📝 开发规范

1. **使用标准库**: 优先使用 `urllib` 而不是 `requests`，减少依赖
2. **错误处理**: 所有脚本都包含 try-except 块处理网络/API错误
3. **退出码**: 脚本返回合适的退出码（0=成功，1=业务错误，2=系统错误）
4. **配置集中**: DS配置和告警配置都集中在脚本顶部的字典中

---

**最后更新**: 2026-03-23
