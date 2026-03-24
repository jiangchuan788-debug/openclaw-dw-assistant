# 智能告警修复系统 - 完整流程文档

## 版本信息
- **版本**: v2.0
- **日期**: 2026-03-24
- **作者**: OpenClaw

---

## 📋 完整流程（7个步骤）

### 步骤1: 扫描数据库告警并发送到OpenClaw

**执行脚本**: `smart_repair_v2.py`

**详细流程**:
1. 连接MySQL数据库 `wattrel`
2. 查询表 `wattrel_quality_alert`
3. 筛选条件:
   - `status = 0` (未处理)
   - `content NOT LIKE '%已恢复%'` (未恢复)
   - `created_at >= NOW() - 24小时` (最近24小时)
4. 按 `level ASC` 排序（P1优先）
5. 将告警列表发送到OpenClaw处理

**关键代码**:
```python
alerts = scanner.scan(hours=24)
# 查询SQL:
# SELECT id, content, type, level, created_at, status
# FROM wattrel_quality_alert
# WHERE created_at >= ? AND status = 0 AND content NOT LIKE '%已恢复%'
# ORDER BY level ASC, created_at DESC
```

---

### 步骤2: 整理告警表并调用search_table.py查找位置

**执行动作**:
1. **解析告警内容**:
   - 提取表名: 正则匹配 `(dwd_\w+|dwb_\w+|ods_\w+|ads_\w+)`
   - 提取dt: 正则匹配 `(\d{4}-\d{2}-\d{2})`
   - 验证dt范围: 不能超过当前时间10天

2. **调用search_table.py**:
   ```bash
   python3 dolphinscheduler/search_table.py <表名> --json
   ```

3. **记录位置信息**:
   - 文件路径: `auto_repair_records/YYYY-MM-DD_table_locations.json`
   - 格式: JSON
   - 写入方式: **覆盖式**（每天一份新记录）
   - 内容示例:
     ```json
     {
       "date": "2026-03-24 10:00:00",
       "tables": {
         "dwd_asset_account_repay": {
           "found": true,
           "workflow_name": "DWD",
           "workflow_code": "158514956979200",
           "task_name": "dwd_asset_account_repay",
           "task_code": "158514956981265"
         }
       }
     }
     ```

---

### 步骤3: 找到工作流后使用启动脚本指定dt重跑

**执行前检查**:

#### 3.1 检查工作流状态（check_running.py）
```bash
python3 dolphinscheduler/check_running.py --workflow-code <工作流Code>
```
- 返回0: 工作流空闲 ✅
- 返回1: 有任务在运行 ⏳等待

#### 3.2 dt值验证规则
```python
# 从告警内容提取dt
示例: 【执行语句】... due_time >= '2026-03-22 00:00:00'
提取dt: '2026-03-22'

# 验证规则
dt_date = datetime.strptime(dt, '%Y-%m-%d')
today = datetime.now()
diff_days = (today - dt_date).days

assert 0 <= diff_days <= 10, "dt超出范围"
```

#### 3.3 启动命令
```bash
# 只启动特定任务（TASK_ONLY）
curl -X POST "http://172.20.0.235:12345/dolphinscheduler/projects/158514956085248/executors/start-process-instance" \
  -H "token: 0cad23ded0f0e942381fc9717c1581a8" \
  -d "processDefinitionCode=<工作流Code>" \
  -d "startNodeList=<任务Code>" \
  -d "taskDependType=TASK_ONLY" \
  -d "failureStrategy=CONTINUE" \
  -d "warningType=NONE" \
  -d "startParams={\"dt\":\"2026-03-22\"}"
```

---

### 步骤4: 限制条件（关键约束）

#### 4.1 工作流状态检查
- 重跑前必须确认工作流空闲
- 使用 `check_running.py` 检查
- 如果忙碌，等待30秒后重试

#### 4.2 同一工作流串行执行
```
场景: 
  - 表A -> DWD工作流
  - 表B -> DWD工作流
  
执行顺序:
  1. 先执行表A（锁定DWD工作流）
  2. 表B等待表A完成
  3. 表B开始执行
```

#### 4.3 最大并行数限制
```python
MAX_PARALLEL = 2  # 最多同时跑2个任务

# 使用信号量控制
semaphore = threading.Semaphore(2)

# 任务分组后并行执行
线程1: 表A (DWD工作流) ──┐
线程2: 表B (DWB工作流) ──┼── 同时执行
线程3: 表C (DWD工作流) ──┘── 等待表A完成
```

#### 4.4 dt值范围限制
```python
# 确认规则
当前时间: 2026-03-24
有效dt范围: [2026-03-14, 2026-03-24] (前后10天)

有效示例:
  ✅ dt='2026-03-22'  (差2天)
  ✅ dt='2026-03-15'  (差9天)
  
无效示例:
  ❌ dt='2026-03-05'  (差19天，超过10天限制)
  ❌ dt='2026-03-25'  (未来日期)
```

#### 4.5 执行前确认
系统会输出执行计划:
```
📋 执行计划:
  1. dwd_asset_account_repay (dt=2026-03-22) -> DWD/dwd_asset_account_repay
  2. dwb_asset_period_info (dt=2026-03-22) -> DWB/dwb_asset_period_info
  3. ...

⚠️ 请确认以上执行计划，检查dt值是否正确
```

---

### 步骤5: 记录重跑次数并执行复验

#### 5.1 记录重跑次数
- 文件: `auto_repair_records/repair_counts.json`
- 格式:
  ```json
  {
    "dwd_asset_account_repay": {
      "2026-03-24": 3,  // 今天重跑了3次
      "2026-03-23": 1
    },
    "dwb_asset_period_info": {
      "2026-03-24": 1
    }
  }
  ```

#### 5.2 执行复验脚本
根据告警级别选择复验工作流:

| 告警级别 | 复验工作流 | 工作流Code |
|---------|-----------|-----------|
| P1 (每日) | 每日复验全级别数据(W-1) | 158515019703296 |
| P1 (每小时) | 每小时复验1级表数据(D-1) | 158515019593728 |
| P2 | 每小时复验2级表数据(D-1) | 158515019630592 |
| P3 | 两小时复验3级表数据(D-1) | 158515019667456 |
| 每周 | 每周复验全级别数据(M-3) | 158515019741184 |
| 每月 | 每月11日复验全级别数据(Y-2) | 158515019778048 |

执行复验:
```bash
# 启动复验工作流
# 等待复验完成（约5-10分钟）
```

---

### 步骤6: 验证修复结果并发送报告

#### 6.1 再次扫描数据库
```python
# 复验后等待1分钟，再次扫描
new_alerts = scanner.scan(hours=1)
```

#### 6.2 对比修复前后
```python
# 检查每个重跑的表是否还在告警中
for table in repaired_tables:
    still_alert = any(table in alert['content'] for alert in new_alerts)
    if still_alert:
        mark_as_failed(table)
    else:
        mark_as_fixed(table)
```

#### 6.3 发送报告到钉钉群

**成功报告示例**:
```
📊 智能告警修复报告

✅ 修复成功 (3个表):
  • dwd_asset_account_repay (dt=2026-03-22) - 重跑成功
  • dwb_asset_period_info (dt=2026-03-22) - 重跑成功
  • ods_biz_erp_withhold (dt=2026-03-22) - 重跑成功

全部修复成功！🎉
```

**失败报告示例**:
```
📊 智能告警修复报告

✅ 修复成功 (2个表):
  • dwd_asset_account_repay (dt=2026-03-22) - 重跑成功
  • dwb_asset_period_info (dt=2026-03-22) - 重跑成功

❌ 修复失败需人工处理 (1个表):
  • ads_report_summary (dt=2026-03-22) - @陈江川
    
该表重跑后仍有告警，请人工排查原因。
```

---

### 步骤7: 记录所有操作

#### 7.1 记录文件夹结构
```
auto_repair_records/
├── 2026-03-24/
│   ├── repair_20260324_100000.log          # 文本日志
│   ├── detail_20260324_100000.json         # 详细数据
│   ├── commands_20260324_100000.sh         # 执行的命令
│   └── thinking_20260324_100000.md         # 思考过程
├── 2026-03-24_table_locations.json         # 表位置记录
├── repair_counts.json                       # 重跑次数统计
└── INDEX.md                                 # 索引文件
```

#### 7.2 记录内容示例

**文本日志** (`repair_*.log`):
```
[10:00:00] [INFO] 🚀 智能告警修复系统 v2.0 启动
[10:00:05] [INFO] 【步骤1】扫描数据库告警
[10:00:10] [INFO] ✅ 扫描到 5 条告警
[10:00:15] [INFO] 【步骤2】解析告警提取表名和dt
...
```

**详细数据** (`detail_*.json`):
```json
{
  "timestamp": "2026-03-24T10:00:00",
  "alerts_scanned": 5,
  "tables_parsed": 3,
  "tasks_executed": 3,
  "results": [...],
  "fixed": ["dwd_asset_account_repay", "dwb_asset_period_info"],
  "failed": ["ads_report_summary"]
}
```

**执行命令** (`commands_*.sh`):
```bash
#!/bin/bash
# 执行时间: 2026-03-24 10:00:00

# 1. 扫描告警
node -e "..."

# 2. 查找表位置
python3 dolphinscheduler/search_table.py dwd_asset_account_repay --json

# 3. 检查工作流状态
python3 dolphinscheduler/check_running.py --workflow-code 158514956979200

# 4. 启动任务
curl -X POST "..." -d "startParams={\"dt\":\"2026-03-22\"}"

# 5. 执行复验
# ...
```

**思考过程** (`thinking_*.md`):
```markdown
# 智能修复思考过程

## 时间: 2026-03-24 10:00:00

## 扫描结果
- 发现5条告警
- 涉及3个唯一表

## 决策过程
1. 表dwd_asset_account_repay -> DWD工作流
   - dt=2026-03-22 (有效，差2天)
   - 工作流空闲，可以执行

2. 表dwb_asset_period_info -> DWB工作流
   - dt=2026-03-22 (有效)
   - 工作流空闲，可以执行

3. 表ads_report_summary -> ADS工作流
   - dt=2026-03-10 (无效，差14天超过限制)
   - ⚠️ 跳过该表

## 执行结果
- 成功: 2个表
- 跳过: 1个表(dt超出范围)
- 失败: 0个表
```

---

## 📁 文件清单

| 文件 | 说明 |
|------|------|
| `smart_repair_v2.py` | 主程序 |
| `dolphinscheduler/search_table.py` | 表位置查找 |
| `dolphinscheduler/check_running.py` | 工作流状态检查 |
| `dolphinscheduler/workflows_export.csv` | 工作流列表 |

---

## 🚀 使用方式

```bash
cd /home/node/.openclaw/workspace
python3 smart_repair_v2.py
```

---

## ⚠️ 注意事项

1. **dt范围**: 严格限制在当前时间前后10天内
2. **并行限制**: 最多同时跑2个任务
3. **工作流锁定**: 同一工作流一次只能跑一个表
4. **状态检查**: 重跑前必须确认工作流空闲
5. **失败处理**: 复验后仍有告警的需要人工介入

---

## 📊 流程图

```
开始
  │
  ▼
扫描告警 ◄─────────────────────────┐
  │                                 │
  ▼                                 │
解析表名和dt                        │
  │                                 │
  ▼                                 │
查找工作流位置                      │
  │                                 │
  ▼                                 │
构建执行计划                        │
  │                                 │
  ▼                                 │
用户确认                            │
  │                                 │
  ▼                                 │
检查工作流状态                      │
  │                                 │
  ├─ 忙碌 ──► 等待30秒 ────────────┤
  │                                 │
  ▼                                 │
获取并行许可                        │
  │                                 │
  ├─ 达到上限 ──► 等待 ────────────┤
  │                                 │
  ▼                                 │
启动单任务                          │
  │                                 │
  ▼                                 │
记录重跑次数                        │
  │                                 │
  ▼                                 │
执行复验                            │
  │                                 │
  ▼                                 │
验证修复结果                        │
  │                                 │
  ├─ 未修复 ──► 标记失败@陈江川    │
  │                                 │
  ▼                                 │
发送报告                            │
  │                                 │
  ▼                                 │
记录操作 ──► 结束                  │
                                   │
◄──────────────────────────────────┘
```

---

**文档完成时间**: 2026-03-24 17:15:00
