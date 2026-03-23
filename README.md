# OpenClaw 数仓智能助手

> OpenClaw + DolphinScheduler + 告警自动化 = 数据工程智能化

---

## 📁 项目结构

```
openclaw-dw-assistant/
├── docs/                           # 文档
│   └── dolphinscheduler-api-guide.md   # DS API 完整指南
│
├── dolphinscheduler/               # DolphinScheduler 调度系统
│   ├── README.md
│   ├── dolphinscheduler_api.py     # 主 API 脚本
│   ├── dolphinscheduler-workflows.csv
│   └── examples/                   # 使用示例
│
├── alert/                          # 告警自动化系统
│   ├── README.md
│   ├── alert_bridge.py             # 告警桥接主脚本
│   ├── send_alert.py
│   ├── check_alerts.py
│   └── examples/                   # 告警示例
│
├── utils/                          # 工具脚本
│   └── daily_summary.py            # 每日总结生成
│
└── memory/                         # OpenClaw 记忆文件
```

---

## 🚀 快速开始

### 1. DolphinScheduler 调度

```python
from dolphinscheduler.dolphinscheduler_api import start_workflow_simple

result = start_workflow_simple(
    project_code="159737550740160",
    process_code="168243093291713",
    dt="2026-03-17"
)
print(f"实例 ID: {result['instance_id']}")
```

[完整指南 →](docs/dolphinscheduler-api-guide.md)

### 2. 告警自动化

```bash
# 启动告警监控
python alert/alert_bridge.py --once

# 每小时定时检查
python alert/alert_bridge_hourly.ps1
```

[告警系统说明 →](alert/README.md)

---

## 📚 文档导航

| 文档 | 说明 |
|------|------|
| [DS API 指南](docs/dolphinscheduler-api-guide.md) | DolphinScheduler API 完整使用指南 |
| [DS 模块说明](dolphinscheduler/README.md) | 调度系统详细说明 |
| [告警模块说明](alert/README.md) | 告警自动化系统说明 |

---

## 🔧 环境要求

- Python 3.8+
- DolphinScheduler 3.x
- OpenClaw (本地部署)
- MySQL (告警数据库)

---

## 📞 联系

作者：陈江川 (江川)

---

**最后更新：** 2026-03-23
