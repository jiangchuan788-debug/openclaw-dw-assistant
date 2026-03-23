# 告警系统脚本清单

本文档梳理 `alert/` 目录下所有告警相关的脚本及其功能。

---

## 📁 核心告警脚本

### 1. alert_bridge.py ⭐ 核心
**用途**: 告警搬运工主脚本（Python版）

**功能**:
- 监控数据库中的未处理告警（`status=0`）
- 将告警格式化后发送给 OpenClaw Webhook
- 自动标记已处理的告警（`status=1`）
- 支持定时任务模式（`--interval`）
- 支持手动触发模式（`--once`）

**配置**:
- 数据库: `172.20.0.235:13306/wattrel`
- Webhook: `http://127.0.0.1:18789/hooks/wattrel/wake`
- Token: `wattrel-webhook-secret-token-2026`

**依赖**: `pymysql`, `requests`

**使用示例**:
```bash
# 手动运行一次
python alert_bridge.py --once

# 持续监控（每30分钟）
python alert_bridge.py --interval 30
```

**输出示例**:
```
============================================================
🚀 OpenClaw 告警雷达 - 手动触发模式
============================================================
📡 Webhook 地址：http://127.0.0.1:18789/hooks/wattrel/wake
💾 数据库：127.0.0.1:3333/wattrel
------------------------------------------------------------

[11:15:30] 🚨 发现 2 条新告警，准备投递给 AI 大脑...
 ✅ 告警 [ID: 12345] 投递成功！
 ✅ 告警 [ID: 12346] 投递成功！
[11:15:31] 数据库回写完毕，已标记为处理完成 (status=1)。

✅ 扫描完成，程序退出。
```

---

### 2. alert_bridge_node.js ⭐ 核心（推荐）
**用途**: 告警搬运工主脚本（Node.js版，推荐）

**功能**:
- 与 `alert_bridge.py` 相同的功能
- 使用 `mysql2` 库连接数据库
- 无需 Python 依赖，直接使用 Node.js

**优势**:
- 在容器中更容易运行（无需安装 Python 依赖）
- 性能更好

**使用示例**:
```bash
# 安装依赖
npm install mysql2

# 运行
node alert_bridge_node.js
```

**输出**:
- 告警文件保存到 `alert/output/` 目录
- 自动标记告警为已处理

---

## 📁 测试和调试脚本

### 3. test_db_connection.py
**用途**: 测试告警数据库连接和查询

**功能**:
- 测试数据库连接
- 查询告警统计（总计/未处理/已处理）
- 列出未处理告警详情（最多10条）

**使用示例**:
```bash
python test_db_connection.py
```

**输出示例**:
```
============================================================
🔍 告警数据库连接测试
============================================================
📍 地址: 172.20.0.235:13306
👤 用户: e_ds
📊 数据库: wattrel

✅ 数据库连接成功！

============================================================
📊 告警统计
============================================================
   总计: 4392 条
   🚨 未处理: 3266 条
   ✅ 已处理: 1126 条

============================================================
🚨 未处理告警列表 (共 10 条)
...
```

---

### 4. debug_alerts.py
**用途**: 告警调试工具

**功能**:
- 调试告警格式化
- 测试数据库连接
- 输出详细的告警字段信息
- 用于排查告警处理问题

**使用示例**:
```bash
python debug_alerts.py
```

---

### 5. check_alerts.py
**用途**: 简单的告警检查脚本

**功能**:
- 快速检查数据库中的告警数量
- 输出未处理告警数量

**使用示例**:
```bash
python check_alerts.py
```

---

## 📁 告警发送脚本

### 6. send_alert.py
**用途**: 告警发送脚本

**功能**:
- 格式化告警消息（转换为钉钉格式）
- 发送告警到 OpenClaw Webhook
- 支持多种告警级别（P1/P2/P3）

**使用场景**:
- 其他脚本调用此脚本发送告警
- 手动发送测试告警
- 自定义告警内容发送

**关键函数**:
```python
def format_alert(alert):
    """格式化告警消息"""
    # 将数据库告警内容转换为钉钉消息格式
    
def send_to_openclaw(message):
    """发送消息到 OpenClaw"""
    # 使用 Webhook 发送
```

---

## 📁 Webhook 测试脚本

### 7. test_webhook.js
**用途**: Webhook 连接测试

**功能**:
- 测试 OpenClaw Webhook 连接
- 发送测试消息到钉钉群
- 验证 Token 和 URL 配置

**使用示例**:
```bash
node test_webhook.js
```

---

### 8. test_format2.py
**用途**: 告警格式测试（备用）

**功能**:
- 测试另一种告警消息格式
- 对比不同格式的显示效果

---

## 📁 PowerShell 脚本

### 9. alert_bridge_hourly.ps1
**用途**: PowerShell 定时任务脚本

**功能**:
- 每小时执行一次告警检查
- 用于 Windows 任务计划程序

**使用示例**:
```powershell
# 创建定时任务
schtasks /Create /TN "OpenClaw Alert Bridge" `
  /TR "powershell.exe -File C:\path\alert_bridge_hourly.ps1" `
  /SC HOURLY
```

---

## 📊 脚本对比表

| 脚本 | 类型 | 主要功能 | 依赖 | 使用频率 | 备注 |
|------|------|---------|------|---------|------|
| `alert_bridge.py` | Python | 告警桥接主脚本 | pymysql, requests | ⭐⭐⭐⭐⭐ | Python版 |
| `alert_bridge_node.js` | Node.js | 告警桥接主脚本 | mysql2 | ⭐⭐⭐⭐⭐ | **推荐** |
| `test_db_connection.py` | Python | 测试数据库连接 | pymysql | ⭐⭐⭐ | 诊断用 |
| `debug_alerts.py` | Python | 调试告警 | pymysql | ⭐⭐ | 排错用 |
| `check_alerts.py` | Python | 简单告警检查 | pymysql | ⭐ | 快速检查 |
| `send_alert.py` | Python | 发送告警 | requests | ⭐⭐⭐ | 被调用 |
| `test_webhook.js` | Node.js | 测试Webhook | 无 | ⭐⭐ | 测试用 |
| `test_format2.py` | Python | 格式测试 | 无 | ⭐ | 备用 |
| `alert_bridge_hourly.ps1` | PowerShell | 定时任务 | PowerShell | ⭐⭐ | Windows用 |

---

## 🚀 推荐使用流程

### 首次配置：
```bash
# 1. 测试数据库连接
cd alert
python test_db_connection.py

# 2. 测试 Webhook 连接
node test_webhook.js

# 3. 运行告警桥接（推荐Node.js版）
node alert_bridge_node.js
```

### 日常监控：
```bash
# 快速检查告警数量
python check_alerts.py

# 详细检查未处理告警
python test_db_connection.py

# 运行告警处理
node alert_bridge_node.js
```

### 故障排查：
```bash
# 如果告警未发送到钉钉
python debug_alerts.py

# 测试 Webhook 是否正常
node test_webhook.js
```

---

## 📝 告警数据库表结构

**表名**: `wattrel_quality_alert`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 告警ID（主键）|
| `content` | text | 告警内容 |
| `type` | int | 告警级别（1=P1, 2=P2, 3=P3）|
| `status` | int | 处理状态（0=未处理, 1=已处理）|
| `created_at` | datetime | 创建时间 |

**常用查询**:
```sql
-- 查询未处理告警
SELECT * FROM wattrel_quality_alert WHERE status = 0;

-- 统计告警
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) as unprocessed,
    SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) as processed
FROM wattrel_quality_alert;
```

---

## 🔗 相关配置

### 数据库连接信息
```python
DB_HOST = '172.20.0.235'
DB_PORT = 13306
DB_USER = 'e_ds'
DB_PASS = 'hAN0Hax1lop'
DB_NAME = 'wattrel'
```

### Webhook 配置
```python
OPENCLAW_WEBHOOK = "http://127.0.0.1:18789/hooks/wattrel/wake"
OPENCLAW_HOOK_TOKEN = "wattrel-webhook-secret-token-2026"
```

---

**最后更新**: 2026-03-23
