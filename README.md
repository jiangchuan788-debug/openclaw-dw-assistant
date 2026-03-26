# 智能告警修复系统

**版本**: v2.6  
**日期**: 2026-03-26

---

## 📋 系统概览

本系统用于自动检测和修复 DolphinScheduler 数据仓库中的数据质量告警，包含两大核心模块：

| 模块 | 功能 | 执行频率 |
|------|------|----------|
| **智能告警修复** | 扫描告警、修复数据、执行复验 | 每日 06:40 |
| **异常调度检测** | 检测并停止异常调度实例 | 每半小时 |

---

## 📁 目录结构

```
.
├── README.md                       # 本文件
├── WORKFLOW_DOCUMENTATION.md       # 完整流程文档
├── EXECUTION_GUIDE.md              # 执行指南
├── STOP_INSTANCE_API.md            # 停止实例API文档
│
├── repair_strict_7step.py          # 主修复脚本（8步流程）⭐
├── auto_stop_abnormal_schedule.py  # 异常调度检测脚本⭐
├── send_tv_report.py               # TV报告发送
├── config.py                       # 配置管理
├── auto_load_env.py                # 环境变量自动加载
│
├── alert/                          # 告警处理模块
│   ├── README.md
│   ├── alert_query_optimized.py    # 告警查询
│   ├── send_alert.py               # 告警发送
│   └── db_config.py                # 数据库配置
│
├── dolphinscheduler/               # DS操作模块
│   ├── README.md
│   ├── check_running.py            # 检查工作流状态
│   ├── search_table.py             # 查找表位置
│   ├── run_fuyan_workflows.py      # 执行复验
│   └── schedules_export.csv        # 调度配置
│
├── auto_repair_records/            # 操作记录
├── cron_jobs/                      # 定时任务导出
└── docs/                           # 其他文档
```

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 设置环境变量
export DS_TOKEN='your_token'
export DB_PASSWORD='your_password'
```

### 2. 手动执行告警修复

```bash
python3 repair_strict_7step.py
```

### 3. 手动执行异常调度检测

```bash
python3 auto_stop_abnormal_schedule.py
```

---

## 📝 核心脚本说明

### repair_strict_7step.py

**8步流程：**
1. 扫描告警表
2. 查找工作流位置
3. 检查工作流状态
4. 执行修复（TASK_ONLY模式）
5. 记录+复验+再次检查
6. 发送钉钉报告
7. 发送TV报告
8. 保存操作记录

**复验智能选择：**
- `dwb_`开头表 → 1级表复验
- 其他表 → 3级表复验
- 每日全级别必跑

---

## ⏰ 定时任务

| 任务 | 频率 | Cron表达式 |
|------|------|-----------|
| 智能告警修复 | 每日 06:40 | `40 6 * * *` |
| 异常调度检测 | 每半小时 | `0,30 * * * *` |

---

## 📚 详细文档

- [完整流程文档](WORKFLOW_DOCUMENTATION.md)
- [执行指南](EXECUTION_GUIDE.md)
- [停止实例API](STOP_INSTANCE_API.md)
- [告警模块](alert/README.md)
- [DS模块](dolphinscheduler/README.md)

---

## 🔧 配置说明

所有敏感配置通过环境变量读取：
- `DS_TOKEN`: DolphinScheduler Token
- `DB_PASSWORD`: 数据库密码
- `DB_HOST`: 数据库主机
- `DB_PORT`: 数据库端口
- `DB_USER`: 数据库用户
- `DB_NAME`: 数据库名称

配置位置：`~/.bashrc`（永久）或通过 `auto_load_env.py` 自动加载

---

**GitHub**: https://github.com/jiangchuan788-debug/openclaw-dw-assistant
