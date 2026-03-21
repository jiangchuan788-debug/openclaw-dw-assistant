# DolphinScheduler API 启动工作流失败报告

**日期：** 2026-03-17 15:51  
**工作流：** market_fee_by_channel  
**项目：** okr_ads  

---

## 📋 基本信息

| 项目 | 值 |
|------|-----|
| 项目 Code | 159737550740160 |
| 工作流 Code | 161876531088065 |
| 工作流名称 | market_fee_by_channel |
| 工作流状态 | ONLINE |
| 工作流版本 | 3 |
| 任务类型 | SQL (StarRocks) |
| 任务环境 Code | 15843695995616 (❌ 不存在) |
| Worker 组 | default |
| 当前用户 | jiangchuanchen (userId: 69, ADMIN_USER) |
| Token | 0cad23ded0f0e942381fc9717c1581a8 |

---

## ❌ API 调用测试

### 测试 1：基础 JSON Body
```powershell
POST /dolphinscheduler/projects/159737550740160/executors/start-process-instance
Content-Type: application/json
Body: {"processDefinitionCode": 161876531088065}
```
**结果：** ❌ 50014 - start process instance error

---

### 测试 2：完整 JSON Body
```powershell
Content-Type: application/json
Body: {
  "processDefinitionCode": 161876531088065,
  "failureStrategy": "CONTINUE",
  "warningType": "NONE",
  "warningGroupId": 0,
  "processInstancePriority": "MEDIUM",
  "workerGroup": "default",
  "dryRun": 0,
  "execType": "START_PROCESS"
}
```
**结果：** ❌ 50014 - start process instance error

---

### 测试 3：Form-Data Body
```powershell
Content-Type: application/x-www-form-urlencoded
Body: processDefinitionCode=161876531088065&failureStrategy=CONTINUE&warningType=NONE&warningGroupId=0&processInstancePriority=MEDIUM&workerGroup=default&dryRun=0
```
**结果：** ❌ 50014 - start process instance error

---

### 测试 4：URL 参数
```powershell
POST /dolphinscheduler/projects/159737550740160/executors/start-process-instance?processDefinitionCode=161876531088065&failureStrategy=CONTINUE&warningType=NONE
```
**结果：** ❌ 50014 - start process instance error

---

### 测试 5：指定环境 Code
```powershell
Content-Type: application/x-www-form-urlencoded
Body: processDefinitionCode=161876531088065&environmentCode=154818709784544&failureStrategy=CONTINUE&warningType=NONE&warningGroupId=0&processInstancePriority=MEDIUM&workerGroup=default&dryRun=0
```
**结果：** ❌ 50014 - start process instance error

---

### 测试 6：浏览器 Fetch API
```javascript
fetch('/dolphinscheduler/projects/159737550740160/executors/start-process-instance', {
  method: 'POST',
  headers: { 'token': '0cad23ded0f0e942381fc9717c1581a8' },
  body: formData // FormData with all parameters
})
```
**结果：** ❌ 50014 - 运行工作流实例错误

---

### 测试 7：重新发布工作流
```powershell
POST /dolphinscheduler/projects/159737550740160/process-definition/161876531088065/release
Body: release=1
```
**结果：** ❌ 10108 - release process definition error

---

## ✅ 已验证正常的项

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 用户认证 | ✅ | Token 有效，可以查询用户信息 |
| 用户权限 | ✅ | ADMIN_USER，项目创建者 |
| 工作流状态 | ✅ | ONLINE (已发布) |
| 工作流查询 | ✅ | 可以查询工作流详情 |
| 任务查询 | ✅ | 可以查询任务列表 |
| 环境列表查询 | ✅ | 可以查询可用环境 |
| 手动启动 | ✅ | Web UI 手动启动正常 |

---

## 🔍 可用环境

| 环境名称 | 环境 Code | 状态 |
|----------|-----------|------|
| prod | 154818922491872 | ✅ 存在 |
| develop | 154818735899616 | ✅ 存在 |
| global | 154818709784544 | ✅ 存在 |

---

## ⚠️ 问题配置

**任务环境 Code：** `15843695995616`

**状态：** ❌ 不存在（查询返回 1200009 - not found environment code）

---

## 🎯 可能的根本原因

1. **任务环境配置无效** - 任务使用的环境 Code `15843695995616` 不存在
2. **环境配置未生效** - 用户说修改了但 API 查询还是旧的环境 Code
3. **DolphinScheduler API Bug** - 特定版本的已知问题
4. **Token 权限限制** - Token 可能只有读权限，没有执行权限

---

## 💡 建议解决方案

### 方案 1：在 Web UI 中确认环境配置

1. 登录 http://127.0.0.1:12345/dolphinscheduler/ui/login
2. 进入 `okr_ads` 项目
3. 找到 `market_fee_by_channel` 工作流
4. 点击 **编辑**
5. 点击任务节点
6. **确认环境字段已改为 `global` 或 `prod`**
7. 点击 **保存**
8. 点击 **发布**（重要！）
9. **刷新页面**，确认环境 Code 已更新

### 方案 2：使用浏览器自动化启动

绕过 API，直接通过浏览器模拟 Web UI 操作启动工作流。

### 方案 3：查看服务端日志

进入 DolphinScheduler 服务器，查看 `logs/dolphinscheduler-api-server.log`，搜索关键词 `50014` 或 `start-process-instance`。

---

## 📝 完整 API 调用命令

```powershell
# 完整调用命令（复制粘贴可用）
$projectCode = "159737550740160"
$processCode = "161876531088065"
$headers = @{ "token" = "0cad23ded0f0e942381fc9717c1581a8" }
$body = "processDefinitionCode=$processCode&failureStrategy=CONTINUE&warningType=NONE&warningGroupId=0&processInstancePriority=MEDIUM&workerGroup=default&dryRun=0"

$response = Invoke-RestMethod -Uri "http://127.0.0.1:12345/dolphinscheduler/projects/$projectCode/executors/start-process-instance" -Method POST -Headers $headers -Body $body -ContentType "application/x-www-form-urlencoded"

Write-Host "响应结果:"
$response | ConvertTo-Json -Depth 5
```

---

## 📊 错误响应

```json
{
    "code": 50014,
    "msg": "start process instance error",
    "data": null,
    "success": false,
    "failed": true
}
```

---

## 📅 下一步行动

1. **在 Web UI 中确认环境配置已更新**
2. **刷新页面后再次查询任务环境 Code**
3. **如果环境 Code 已更新，重新测试 API 调用**
4. **如果还是失败，查看服务端日志**

---

**生成时间：** 2026-03-17 15:51:00 GMT+8
