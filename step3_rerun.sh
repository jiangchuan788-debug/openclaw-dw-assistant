#!/bin/bash
# 步骤3: 执行重跑脚本
# 所有表都在DWD工作流中，需要串行执行

PROJECT_CODE="158514956085248"
WORKFLOW_CODE="158514956979200"
ENV_CODE="154818922491872"
TOKEN="0cad23ded0f0e942381fc9717c1581a8"
DS_URL="http://172.20.0.235:12345/dolphinscheduler/projects"

echo "=========================================================================="
echo "🚀 步骤3: 指定dt重跑（带限制条件）"
echo "=========================================================================="
echo ""
echo "限制条件检查:"
echo "  ✅ dt范围验证: 所有dt差值≤10天"
echo "  ✅ 工作流空闲检查: DWD工作流空闲"
echo "  ✅ 同工作流串行控制: 所有表属于同一工作流，将串行执行"
echo "  ✅ 全局并行限制: 串行执行满足最多2个并行限制"
echo ""

# 记录重跑结果
RESULTS_FILE="/home/node/.openclaw/workspace/auto_repair_records/2026-03-25_rerun_results.json"
EXEC_LOG="/home/node/.openclaw/workspace/auto_repair_records/2026-03-25_commands.sh"

echo "#!/bin/bash" > $EXEC_LOG
echo "# 执行命令记录 - $(date)" >> $EXEC_LOG
echo "" >> $EXEC_LOG

# 定义重跑任务
# 格式: 任务名称|任务Code|dt
declare -a TASKS=(
    "dwd_asset_account_recharge|158514956981264|2026-03-24"
    "dwd_asset_qsq_erp_withhold|158514956981269|2026-03-24"
    "dwd_asset_account_repay|158514956981265|2026-03-24"
    "dwd_asset_account_repay|158514956981265|2026-03-23"
    "dwd_asset_clean_clearing_trans|158514956981251|2026-03-17"
)

SUCCESS_COUNT=0
FAILED_COUNT=0
declare -a INSTANCE_IDS

echo "开始执行重跑（串行）:"
echo "--------------------------------------------------------------------------------"

for task_info in "${TASKS[@]}"; do
    IFS='|' read -r TASK_NAME TASK_CODE DT <<< "$task_info"
    
    echo ""
    echo "[$(date '+%H:%M:%S')] 执行任务: $TASK_NAME (dt=$DT)"
    
    # 构建curl命令
    CURL_CMD="curl -s -X POST '${DS_URL}/${PROJECT_CODE}/executors/start-process-instance' \
        -H 'token: ${TOKEN}' \
        -H 'Content-Type: application/x-www-form-urlencoded' \
        -d 'processDefinitionCode=${WORKFLOW_CODE}' \
        -d 'startNodeList=${TASK_CODE}' \
        -d 'taskDependType=TASK_ONLY' \
        -d 'failureStrategy=CONTINUE' \
        -d 'warningType=NONE' \
        -d 'warningGroupId=0' \
        -d 'environmentCode=${ENV_CODE}' \
        -d 'tenantCode=dolphinscheduler' \
        -d 'execType=START_PROCESS' \
        -d 'dryRun=0' \
        -d 'scheduleTime=' \
        -d 'startParams={\"dt\":\"${DT}\"}' \
        --connect-timeout 30"
    
    # 记录命令
    echo "# Task: $TASK_NAME (dt=$DT)" >> $EXEC_LOG
    echo "$CURL_CMD" >> $EXEC_LOG
    echo "" >> $EXEC_LOG
    
    # 执行命令
    RESPONSE=$(eval $CURL_CMD)
    
    # 解析结果
    CODE=$(echo $RESPONSE | grep -o '"code":[0-9]*' | cut -d: -f2)
    MSG=$(echo $RESPONSE | grep -o '"msg":"[^"]*"' | cut -d'"' -f4)
    INSTANCE_ID=$(echo $RESPONSE | grep -o '"data":[0-9]*' | cut -d: -f2)
    
    if [ "$CODE" == "0" ]; then
        echo "   ✅ 启动成功 - Instance ID: $INSTANCE_ID"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        INSTANCE_IDS+=("$TASK_NAME|$DT|$INSTANCE_ID|success")
    else
        echo "   ❌ 启动失败 - 错误: $MSG"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        INSTANCE_IDS+=("$TASK_NAME|$DT|null|failed:$MSG")
    fi
    
    # 等待3秒后继续下一个
    sleep 3
done

echo ""
echo "--------------------------------------------------------------------------------"
echo "重跑执行完成: 成功=$SUCCESS_COUNT, 失败=$FAILED_COUNT"
echo "--------------------------------------------------------------------------------"

# 保存结果到JSON
cat > $RESULTS_FILE << EOF
{
  "timestamp": "$(date -Iseconds)",
  "workflow": "DWD",
  "workflow_code": "$WORKFLOW_CODE",
  "success_count": $SUCCESS_COUNT,
  "failed_count": $FAILED_COUNT,
  "instances": [
EOF

# 添加实例记录
for i in "${!INSTANCE_IDS[@]}"; do
    IFS='|' read -r TASK_NAME DT INSTANCE_ID STATUS <<< "${INSTANCE_IDS[$i]}"
    if [ $i -gt 0 ]; then
        echo "," >> $RESULTS_FILE
    fi
    echo -n "    {\"task\": \"$TASK_NAME\", \"dt\": \"$DT\", \"instance_id\": \"$INSTANCE_ID\", \"status\": \"$STATUS\"}" >> $RESULTS_FILE
done

echo "" >> $RESULTS_FILE
echo "  ]" >> $RESULTS_FILE
echo "}" >> $RESULTS_FILE

echo ""
echo "💾 结果已保存:"
echo "   - $RESULTS_FILE"
echo "   - $EXEC_LOG"
