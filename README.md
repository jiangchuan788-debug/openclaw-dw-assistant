# 智能告警修复系统

**版本**: v2.12  
**日期**: 2026-03-26  
**作者**: OpenClaw

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
├── README.md                    # 本文件 - 项目入口
├── SYSTEM_MEMORY.md             # 系统记忆摘要 - 关键信息速查
│
├── config/                      # 配置模块
│   ├── config.py                # 配置管理
│   ├── auto_load_env.py         # 环境变量自动加载
│   └── README.md
│
├── core/                        # 核心定时任务 ⭐
│   ├── auto_stop_abnormal_schedule.py  # 异常调度检测
│   ├── repair_strict_7step.py          # 智能告警修复
│   ├── send_tv_report.py               # TV报告发送
│   └── README.md
│
├── modules/                     # 功能模块
│   ├── alert/                   # 告警处理模块
│   │   ├── alert_query_optimized.py
│   │   ├── send_alert.py
│   │   ├── db_config.py
│   │   └── README.md
│   │
│   └── dolphinscheduler/        # DS操作模块
│       ├── check_running.py
│       ├── search_table.py
│       ├── run_fuyan_workflows.py
│       ├── schedules_export.csv
│       └── README.md
│
├── tools/                       # 工具脚本
│   ├── extract_ds_sql.py        # SQL提取工具
│   ├── task_execution_checker.py # 执行检查工具
│   └── README.md
│
├── docs/                        # 文档
│   ├── WORKFLOW_DOCUMENTATION.md       # 完整流程文档
│   ├── TASK_EXECUTION_WORKFLOW.md      # 执行流程详解
│   ├── EXECUTION_GUIDE.md              # 执行指南
│   ├── STOP_INSTANCE_API.md            # API文档
│   └── README.md
│
├── templates/                   # 配置文件模板
│   ├── AGENTS.md.template
│   ├── SOUL.md.template
│   ├── USER.md.template
│   ├── TOOLS.md.template
│   ├── IDENTITY.md.template
│   ├── BOOTSTRAP.md.template
│   └── README.md
│
├── data/                        # 数据文件
│   ├── cron_jobs/               # 定时任务记录
│   ├── auto_repair_records/     # 操作记录
│   └── README.md
│
└── memory/                      # 每日记忆记录
```

---

## 🚀 快速开始

### 环境准备

```bash
# 设置环境变量（在 ~/.bashrc 中）
export DS_TOKEN='your_token'
export DB_PASSWORD='your_password'
```

### 首次部署（复现指南）

```bash
# 1. 克隆代码
git clone https://github.com/jiangchuan788-debug/openclaw-dw-assistant.git
cd openclaw-dw-assistant

# 2. 初始化配置（复制模板）
cp templates/AGENTS.md.template AGENTS.md
cp templates/SOUL.md.template SOUL.md
cp templates/USER.md.template USER.md
cp templates/TOOLS.md.template TOOLS.md
cp templates/IDENTITY.md.template IDENTITY.md

# 编辑这些文件，填写你的配置...

# 3. 配置环境变量
source ~/.bashrc

# 4. 验证配置
python3 tools/task_execution_checker.py --task all

# 5. 测试执行
python3 core/auto_stop_abnormal_schedule.py
python3 core/repair_strict_7step.py
```

### 手动执行

```bash
# 异常调度检测
python3 core/auto_stop_abnormal_schedule.py

# 智能告警修复
python3 core/repair_strict_7step.py
```

---

## 📝 核心脚本说明

### 1. 异常调度检测 (`core/auto_stop_abnormal_schedule.py`)

**8步执行流程：**
1. 加载调度配置
2. 获取运行中实例
3. 异常检测
4. 自动停止异常实例
5. TV通知（有条件）
6. 钉钉报告（已禁用）
7. 保存检测记录
8. 执行完成

**通知策略：** 只有发现异常时才发送TV通知，正常情况下静默

### 2. 智能告警修复 (`core/repair_strict_7step.py`)

**8步执行流程：**
1. 扫描告警（单次执行内去重）
2. 查找工作流位置
3. 执行修复（带限制检查）
4. 记录+复验（智能选择）
5. 钉钉报告（已禁用）
6. 保存操作记录
7. TV报告
8. 执行完成

**复验智能选择：**
- `dwb_`开头表 → 1级表复验
- 其他表 → 3级表复验
- 每日全级别必跑

---

## 🔧 常用工具

### 提取 SQL 代码

```bash
python3 tools/extract_ds_sql.py <project_code> --name <project_name>

# 示例
python3 tools/extract_ds_sql.py 159737550740160 --name okr_ads
```

### 检查任务环境

```bash
python3 tools/task_execution_checker.py --task all
```

---

## 📚 详细文档

| 文档 | 用途 | 位置 |
|------|------|------|
| **SYSTEM_MEMORY.md** | 系统记忆摘要 - 关键信息速查 | 根目录 |
| **WORKFLOW_DOCUMENTATION.md** | 完整系统流程文档 | docs/ |
| **TASK_EXECUTION_WORKFLOW.md** | 定时任务执行流程详解 | docs/ |
| **EXECUTION_GUIDE.md** | 执行指南 | docs/ |
| **STOP_INSTANCE_API.md** | 停止实例API文档 | docs/ |

---

## 🔑 关键配置

### 环境变量

```bash
DS_TOKEN              # DolphinScheduler Token
DB_PASSWORD           # 数据库密码
DB_HOST=172.20.0.235  # 数据库主机
DB_PORT=13306         # 数据库端口
DB_USER=e_ds          # 数据库用户
DB_NAME=wattrel       # 数据库名称
```

### 项目代码

| 项目名称 | Code |
|---------|------|
| 国内数仓-工作流 | 158514956085248 |
| 国内数仓-质量校验 | 158515019231232 |
| okr_ads | 159737550740160 |

---

## ⏰ 定时任务

| 任务 | 频率 | 超时 |
|------|------|------|
| 异常调度检测 | 每半小时（00,30分） | 300秒 |
| 智能告警修复 | 每日 06:40 | 1800秒 |

---

## 📞 联系信息

- **GitHub**: https://github.com/jiangchuan788-debug/openclaw-dw-assistant
- **用途**: 数据仓库监控和告警自动修复

---

**更多信息请查看 [docs/](./docs/) 目录下的文档。**
