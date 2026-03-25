#!/bin/bash
# 执行的命令记录

# 步骤1: 扫描告警
python3 alert/alert_query_optimized.py

# 步骤2: 查找工作流位置
python3 dolphinscheduler/search_table.py dwd_asset_account_repay

# 步骤3: 启动任务（带dt参数）
# dwd_asset_account_repay (dt=2026-03-23)
curl -X POST .../executors/start-process-instance \
  -d 'processDefinitionCode=158514956979200' \
  -d 'startNodeList=158514956981265' \
  -d 'taskDependType=TASK_ONLY' \
  -d 'startParams={\"dt\":\"2026-03-23\"}'

# 步骤4: 执行复验（全部6个）
# 每日复验全级别数据(W-1)
curl -X POST .../executors/start-process-instance -d 'processDefinitionCode=158515019703296'
# 每小时复验1级表数据(D-1)
curl -X POST .../executors/start-process-instance -d 'processDefinitionCode=158515019593728'
# 每小时复验2级表数据(D-1)
curl -X POST .../executors/start-process-instance -d 'processDefinitionCode=158515019630592'
# 两小时复验3级表数据(D-1)
curl -X POST .../executors/start-process-instance -d 'processDefinitionCode=158515019667456'
# 每周复验全级别数据(M-3)
curl -X POST .../executors/start-process-instance -d 'processDefinitionCode=158515019741184'
# 每月11日复验全级别数据(Y-2)
curl -X POST .../executors/start-process-instance -d 'processDefinitionCode=158515019778048'
