# 告警自动化模块

> 数据质量告警实时监控与 OpenClaw 智能处理

---

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `alert_bridge.py` | 告警搬运工主脚本，核心模块 |
| `send_alert.py` | 告警发送脚本 |
| `check_alerts.py` | 告警检查脚本 |
| `debug_alerts.py` | 调试工具 |
| `alert_bridge_hourly.ps1` | PowerShell 定时任务脚本 |
| `examples/` | 测试和示例代码 |

---

## 🏗️ 系统架构

```
数据库告警表 ──→ alert_bridge.py ──→ OpenClaw Webhook ──→ 钉钉群
wattrel_quality                          /hooks/wattrel
_alert
```

---

## 🚀 快速开始

### 1. 配置参数

编辑 `alert_bridge.py`：
```python
# 数据库配置 (告警系统内网映射地址)
DB_HOST = '172.20.0.235'    # 内网映射地址
DB_PORT = 13306              # 映射端口
DB_USER = 'e_ds'            # 用户名
DB_PASS = '密码'            # 密码
DB_NAME = 'wattrel'         # 数据库名

# OpenClaw 本地 Webhook 地址
OPENCLAW_WEBHOOK = "http://127.0.0.1:18789/hooks/wattrel/wake"
OPENCLAW_HOOK_TOKEN = "MySecretAlertToken123"
```

### 2. 手动执行测试

```bash
python alert_bridge.py --once
```

### 3. 配置定时任务（Windows）

```powershell
schtasks /Create /TN "OpenClaw Alert Bridge" `
  /TR "python C:\path\to\alert_bridge.py --once" `
  /SC HOURLY
```

---

## 📊 告警格式

**输入（数据库）：**
```
指标校验异常 ods_qsq_erp_atransaction 数量不一致...
【执行语句】SELECT COUNT(*)...
```

**输出（钉钉群）：**
```
【任务名称】数据质量校验任务_12345
【告警时间】2026-03-18 17:50:42
【告警级别】P3
【告警内容】...
【执行语句】...
```

---

## ⚠️ 注意事项

1. **SSH 隧道** - 远程数据库需先建立隧道
2. **Token 安全** - 不要将 Token 提交到仓库
3. **状态回写** - 处理后自动更新 status=1
4. **重复告警** - 通过 status 字段防止重复发送

---

## 🔧 测试

```bash
# 测试数据库连接
python check_alerts.py

# 调试模式
python debug_alerts.py

# 格式化测试
python examples/test_alert_format.py
```

---

**最后更新：** 2026-03-23
