#!/bin/bash
# 步骤4: 执行全部6个复验工作流

PROJECT_CODE="158515019231232"
ENV_CODE="154818922491872"
TOKEN="0cad23ded0f0e942381fc9717c1581a8"
DS_URL="http://172.20.0.235:12345/dolphinscheduler/projects"

echo "=========================================================================="
echo "🧪 步骤4.2: 执行全部6个复验工作流"
echo "=========================================================================="

# 复验工作流列表
declare -a FUYAN_WORKFLOWS=(
    "每日复验全级别数据(W-1)|158515019703296"
    "每小时复验1级表数据(D-1)|158515019593728"
    "每小时复验2级表数据(D-1)|158515019630592"
    "两小时复验3级表数据(D-1)|158515019667456"
    "每周复验全级别数据(M-3)|158515019741184"
    "每月11日复验全级别数据(Y-2)|158515019778048"
)

SUCCESS_COUNT=0
declare -a FUYAN_RESULTS

echo ""
echo "启动复验工作流:"
echo "--------------------------------------------------------------------------------"

for wf_info in "${FUYAN_WORKFLOWS[@]}"; do
    IFS='|' read -r WF_NAME WF_CODE <<< "$wf_info"
    
    echo ""
    echo "[$(date '+%H:%M:%S')] 启动: $WF_NAME"
    
    # 构建curl命令
    CURL_CMD="curl -s -X POST '${DS_URL}/${PROJECT_CODE}/executors/start-process-instance' \
        -H 'token: ${TOKEN}' \
        -H 'Content-Type: application/x-www-form-urlencoded' \
        -d 'processDefinitionCode=${WF_CODE}' \
        -d 'failureStrategy=CONTINUE' \
        -d 'warningType=NONE' \
        -d 'environmentCode=${ENV_CODE}' \
        -d 'tenantCode=dolphinscheduler' \
        -d 'execType=START_PROCESS' \
        -d 'dryRun=0' \
        -d 'scheduleTime=' \
        --connect-timeout 30"
    
    # 执行命令
    RESPONSE=$(eval $CURL_CMD)
    
    # 解析结果
    CODE=$(echo $RESPONSE | grep -o '"code":[0-9]*' | cut -d: -f2)
    INSTANCE_ID=$(echo $RESPONSE | grep -o '"data":[0-9]*' | cut -d: -f2)
    
    if [ "$CODE" == "0" ]; then
        echo "   ✅ 启动成功 - Instance ID: $INSTANCE_ID"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        FUYAN_RESULTS+=("$WF_NAME|$INSTANCE_ID|success")
    else
        echo "   ❌ 启动失败"
        FUYAN_RESULTS+=("$WF_NAME|null|failed")
    fi
    
    # 等待2秒后继续下一个
    sleep 2
done

echo ""
echo "--------------------------------------------------------------------------------"
echo "复验工作流启动完成: $SUCCESS_COUNT/6 成功"
echo "--------------------------------------------------------------------------------"

# 保存结果
FUYAN_FILE="/home/node/.openclaw/workspace/auto_repair_records/2026-03-25_fuyan_results.json"
cat > $FUYAN_FILE << EOF
{
  "timestamp": "$(date -Iseconds)",
  "success_count": $SUCCESS_COUNT,
  "total": 6,
  "workflows": [
EOF

for i in "${!FUYAN_RESULTS[@]}"; do
    IFS='|' read -r WF_NAME INSTANCE_ID STATUS <<< "${FUYAN_RESULTS[$i]}"
    if [ $i -gt 0 ]; then
        echo "," >> $FUYAN_FILE
    fi
    echo -n "    {\"name\": \"$WF_NAME\", \"instance_id\": \"$INSTANCE_ID\", \"status\": \"$STATUS\"}" >> $FUYAN_FILE
done

echo "" >> $FUYAN_FILE
echo "  ]" >> $FUYAN_FILE
echo "}" >> $FUYAN_FILE

echo ""
echo "💾 复验结果已保存: $FUYAN_FILE"
echo ""
echo "⏳ 等待复验完成 (等待60秒)..."
sleep 60
echo "✅ 等待完成"
