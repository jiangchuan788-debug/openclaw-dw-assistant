# 智能告警修复流程 - 执行文档

## 📋 文档信息
- **版本**: v1.0
- **创建日期**: 2026-03-24
- **执行环境**: OpenClaw + DolphinScheduler
- **工作目录**: `/home/node/.openclaw/workspace`

---

## 🎯 执行前准备

### 1. 确认当前工作目录
```bash
cd /home/node/.openclaw/workspace
pwd  # 确认输出: /home/node/.openclaw/workspace
```

### 2. 检查必要脚本是否存在
```bash
ls -la alert/alert_query_optimized.py
ls -la dolphinscheduler/search_table.py
ls -la dolphinscheduler/check_running.py
ls -la repair_strict_7step.py
```

### 3. 确认DS服务可访问
```bash
curl -s "http://172.20.0.235:12345/dolphinscheduler/projects/158514956085248/process-definition?pageNo=1&pageSize=5" \
  -H "token: 0cad23ded0f0e942381fc9717c1581a8" | head -20
```

---

## 🚀 正式执行流程

### 【步骤1】扫描数据库告警

**操作命令**:
```bash
cd /home/node/.openclaw/workspace/alert
python3 alert_query_optimized.py
```

**预期输出**:
```
======================================================================
🚀 数据质量告警查询
======================================================================
[*] 查询时间范围: 2026-03-23 00:00:00 至 2026-03-24 23:59:59
[!] 发现 X 条未处理告警
[1/X] 推送告警 ID:xxxx...
   ✅ 推送成功
...
```

**检查点**:
- [ ] 告警已推送到钉钉群
- [ ] 记录告警ID列表
- [ ] 确认告警内容为"未恢复"

**记录到日志**:
```bash
echo "$(date '+%Y-%m-%d %H:%M:%S') - 步骤1完成 - 发现X条告警" >> ../auto_repair_logs/execute_$(date +%Y%m%d).log
```

---

### 【步骤2】整理告警表，查找工作流位置

#### 2.1 解析告警内容，提取表名和dt

**告警内容解析规则**:
```
表名提取: 匹配 (dwd_\w+|dwb_\w+|ods_\w+|ads_\w+)
dt提取: 从执行语句中提取日期 'YYYY-MM-DD'
```

**示例**:
```
告警内容包含:
  "dwb_asset_period_info dwb_asset_period_info_penalty_amt(申请借款金额统计)不一致"
  "due_time >= '2026-03-22 00:00:00'"
  
提取结果:
  表名: dwb_asset_period_info
  dt: 2026-03-22
```

#### 2.2 对每个表调用search_table.py查找位置

**操作命令**（以dwb_asset_period_info为例）:
```bash
cd /home/node/.openclaw/workspace/dolphinscheduler
python3 search_table.py dwb_asset_period_info
```

**预期输出**:
```
====================================================================================================
🔍 在 [国内数仓-工作流] 中搜索: 'dwb_asset_period_info'
...
✅ 找到 X 个工作流包含 'dwb_asset_period_info':

[1] 📋 工作流: DWB
    工作流Code: 158514957297664
    状态: ONLINE
    ...
    [1] 任务: dwb_asset_period_info
        任务Code: 158514957297701
```

#### 2.3 记录表位置（每天一份，覆盖式写入）

**操作命令**:
```bash
cat > /home/node/.openclaw/workspace/auto_repair_records/$(date +%Y-%m-%d)_table_locations.json << 'EOF'
{
  "date": "$(date -Iseconds)",
  "tables": {
    "表名1": {
      "table": "表名1",
      "dt": "2026-03-22",
      "level": "P1",
      "workflow_name": "工作流名称",
      "workflow_code": "工作流Code",
      "task_name": "任务名称",
      "task_code": "任务Code"
    },
    "表名2": { ... }
  }
}
EOF
```

**检查点**:
- [ ] 每个告警表都找到对应的工作流
- [ ] 工作流状态为ONLINE
- [ ] 记录文件已保存

---

### 【步骤3】指定dt重跑（带限制条件）

#### 3.1 制定执行计划

**输出执行计划表格**:
```
执行计划:
序号 | 表名 | dt | 工作流 | 任务Code | dt差值 | 状态
-----|------|----|--------|----------|--------|------
1    | xxx  | xxx| xxx    | xxx      | X天    | 待检查
2    | xxx  | xxx| xxx    | xxx      | X天    | 待检查
```

#### 3.2 限制条件检查

**检查1: dt范围验证（≤10天）**
```python
# 伪代码逻辑
dt_date = datetime.strptime(dt, '%Y-%m-%d')
today = datetime.now()
diff_days = (today - dt_date).days

if diff_days > 10:
    跳过该表，记录"dt超出范围"
elif diff_days < 0:
    跳过该表，记录"dt为未来日期"
else:
    继续执行
```

**检查2: 工作流空闲检查**
```bash
cd /home/node/.openclaw/workspace/dolphinscheduler
python3 check_running.py --check-only -f "工作流名称"
# 返回码: 0=空闲, 1=忙碌
```

**检查3: 同工作流串行控制**
```python
# 如果多个表属于同一个工作流，需要串行执行
# 使用锁或等待机制
```

**检查4: 全局并行限制（最多2个）**
```python
# 使用信号量控制
MAX_PARALLEL = 2
```

#### 3.3 执行重跑

**构建启动命令**（示例）:
```bash
curl -s -X POST 'http://172.20.0.235:12345/dolphinscheduler/projects/158514956085248/executors/start-process-instance' \
  -H 'token: 0cad23ded0f0e942381fc9717c1581a8' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'processDefinitionCode=工作流Code' \
  -d 'startNodeList=任务Code' \
  -d 'taskDependType=TASK_ONLY' \
  -d 'failureStrategy=CONTINUE' \
  -d 'warningType=NONE' \
  -d 'warningGroupId=0' \
  -d 'environmentCode=154818922491872' \
  -d 'tenantCode=dolphinscheduler' \
  -d 'execType=START_PROCESS' \
  -d 'dryRun=0' \
  -d 'scheduleTime=' \
  -d 'startParams={"dt":"2026-03-22"}' \
  --connect-timeout 30
```

**检查点**:
- [ ] 返回code=0，msg=success
- [ ] 记录instance_id
- [ ] 等待3秒后继续下一个

---

### 【步骤4】记录重跑次数 + 执行复验 + 再次检查告警

#### 4.1 记录重跑次数

**操作命令**:
```bash
cat >> /home/node/.openclaw/workspace/auto_repair_records/repair_counts.json << 'EOF'
{
  "表名": {
    "2026-03-24": 1  // 今日第1次
  }
}
EOF
```

#### 4.2 执行全部6个复验工作流

**复验工作流列表**:
| 序号 | 名称 | Code |
|-----|------|------|
| 1 | 每日复验全级别数据(W-1) | 158515019703296 |
| 2 | 每小时复验1级表数据(D-1) | 158515019593728 |
| 3 | 每小时复验2级表数据(D-1) | 158515019630592 |
| 4 | 两小时复验3级表数据(D-1) | 158515019667456 |
| 5 | 每周复验全级别数据(M-3) | 158515019741184 |
| 6 | 每月11日复验全级别数据(Y-2) | 158515019778048 |

**启动命令**（示例）:
```bash
curl -s -X POST 'http://172.20.0.235:12345/dolphinscheduler/projects/158515019231232/executors/start-process-instance' \
  -H 'token: 0cad23ded0f0e942381fc9717c1581a8' \
  -d 'processDefinitionCode=158515019703296' \
  -d 'failureStrategy=CONTINUE' \
  -d 'environmentCode=154818922491872' \
  -d 'tenantCode=dolphinscheduler' \
  -d 'execType=START_PROCESS' \
  -d 'dryRun=0' \
  -d 'scheduleTime='
```

**等待复验完成**:
```bash
sleep 300  # 等待5分钟
```

#### 4.3 再次检查数据库告警

**操作命令**:
```bash
cd /home/node/.openclaw/workspace/alert
python3 alert_query_optimized.py
```

**对比修复前后**:
- 修复前的告警表是否还在列表中？
- 如果还在 → 标记为失败
- 如果不在 → 标记为成功

---

### 【步骤5】发送修复报告到钉钉

**报告模板**:
```
📊 智能告警修复报告

✅ 以下表通过按照指定dt重跑的方式修复成功:
  • 表名1 (dt=2026-03-22) - 实例ID: xxx
  • 表名2 (dt=2026-03-23) - 实例ID: xxx

❌ 以下表修复失败，需要人工处理:
  • 表名3 (dt=2026-03-22) - @陈江川
    错误: xxx
  • 表名4 (dt=2026-03-23) - @陈江川
    错误: xxx

🔄 复验执行: 6/6 个工作流已启动
```

**发送命令**:
```bash
openclaw message send --channel dingtalk-connector \
  --target "group:cidune9y06rl1j0uelxqielqw==" \
  --message "报告内容"
```

---

### 【步骤6】保存操作记录

**创建记录目录**:
```bash
mkdir -p /home/node/.openclaw/workspace/auto_repair_records/$(date +%Y-%m-%d)
```

**保存3类文件**:

1. **详细数据** (`detail_YYYYMMDD_HHMMSS.json`):
```json
{
  "timestamp": "2026-03-24T19:00:00",
  "tasks": [...],
  "fuyan_results": [...],
  "fixed": ["表名1", "表名2"],
  "failed": ["表名3"]
}
```

2. **执行命令** (`commands_YYYYMMDD_HHMMSS.sh`):
```bash
#!/bin/bash
# 所有执行的curl命令
...
```

3. **思考过程** (`thinking_YYYYMMDD_HHMMSS.md`):
```markdown
# 执行记录
## 时间: xxx
## 步骤1: ...
## 步骤2: ...
...
```

---

## 📝 执行记录模板

每次执行后填写：

```
执行日期: 2026-03-24
执行人: OpenClaw
告警数量: X条
修复成功: X个表
修复失败: X个表
复验状态: 6/6 成功
记录路径: auto_repair_records/2026-03-24/
```

---

## ⚠️ 常见问题处理

### 问题1: search_table.py找不到表
**解决**: 尝试使用表名关键字（如'account_repay'而非完整表名）

### 问题2: check_running.py返回忙碌
**解决**: 循环等待，最多等待5分钟

### 问题3: 启动API返回50014错误
**解决**: 
1. 检查工作流是否真的空闲
2. 确认任务Code正确
3. 使用完整参数（包含environmentCode等）

### 问题4: dt参数未正确传递
**解决**: 检查startParams JSON格式是否正确转义

---

## 🔗 相关文件索引

| 文件 | 用途 |
|------|------|
| `alert/alert_query_optimized.py` | 告警扫描 |
| `dolphinscheduler/search_table.py` | 表位置查找 |
| `dolphinscheduler/check_running.py` | 工作流状态检查 |
| `dolphinscheduler/run_fuyan_workflows.py` | 复验工作流 |
| `repair_strict_7step.py` | 完整自动化脚本 |
| `dolphinscheduler/workflows_export.csv` | 工作流列表参考 |

---

## ✅ 执行确认清单

执行完成后检查：
- [ ] 步骤1: 告警已推送钉钉
- [ ] 步骤2: 表位置已记录到JSON文件
- [ ] 步骤3: 重跑任务已启动（检查instance_id）
- [ ] 步骤4: 6个复验工作流已启动
- [ ] 步骤5: 报告已发送到钉钉群
- [ ] 步骤6: 3类记录文件已保存

---

**文档结束**
