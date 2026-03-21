# DolphinScheduler API 调用指南

> 版本：v1.1  
> 更新日期：2026-03-17  
> 目标环境：http://127.0.0.1:12345

---

## 📋 目录

1. [认证方式](#认证方式)
2. [API 调用方法](#api-调用方法)
3. [可用 API 列表](#可用 api 列表)
4. [实际调用示例](#实际调用示例)
5. [常见问题](#常见问题)

---

## 🔐 认证方式

### 令牌认证（推荐）⭐

**获取 Token 步骤：**

1. 登录 DolphinScheduler Web UI
2. 点击 **安全中心** → **令牌管理**
3. 点击 **创建令牌**
4. 设置失效时间和用户
5. 生成并拷贝 Token

**使用方式：**

所有 API 请求需要在 Header 中携带 Token：

```http
token: <你的 Token>
Content-Type: application/json
```

**当前环境配置：**

```powershell
$token = "0cad23ded0f0e942381fc9717c1581a8"
$baseUrl = "http://127.0.0.1:12345/dolphinscheduler"
$headers = @{
    "token" = $token
    "Content-Type" = "application/json"
}
```

---

## 💻 API 调用方法

### PowerShell Invoke-RestMethod

```powershell
$headers = @{
    "token" = "0cad23ded0f0e942381fc9717c1581a8"
    "Content-Type" = "application/json"
}

$response = Invoke-RestMethod -Uri "http://127.0.0.1:12345/dolphinscheduler/api-path" -Method GET -Headers $headers
$response | ConvertTo-Json -Depth 10
```

### 浏览器 Fetch API（用于调试）

```javascript
fetch('/dolphinscheduler/api-path', {
    headers: {
        'token': '0cad23ded0f0e942381fc9717c1581a8'
    }
}).then(r => r.json()).then(d => console.log(d))
```

---

## 📚 可用 API 列表

### 用户相关

| 功能 | API 路径 | 方法 | 状态 |
|------|----------|------|------|
| 获取当前用户信息 | `/users/get-user-info` | GET | ✅ 可用 |

**示例：**
```powershell
Invoke-RestMethod -Uri "$baseUrl/users/get-user-info" -Method GET -Headers $headers
```

---

### 项目相关

| 功能 | API 路径 | 方法 | 状态 |
|------|----------|------|------|
| 查询项目列表 | `/projects` | GET | ✅ 可用 |
| 查询项目详情（按 Code） | `/projects/{projectCode}` | GET | ✅ 可用 |
| 查询项目详情（按 ID） | `/projects/query-by-code?projectCode={code}` | GET | ⚠️ 可能失败 |

**示例：**
```powershell
# 查询所有项目
Invoke-RestMethod -Uri "$baseUrl/projects?pageSize=130&pageNo=1" -Method GET -Headers $headers

# 查询项目详情
Invoke-RestMethod -Uri "$baseUrl/projects/158514956085248" -Method GET -Headers $headers
```

---

### 工作流定义相关 ⭐

| 功能 | API 路径 | 方法 | 状态 |
|------|----------|------|------|
| 查询工作流列表 | `/projects/{projectCode}/process-definition/query-process-definition-list` | GET | ✅ 可用（推荐） |
| 查询工作流列表（分页） | `/projects/{projectCode}/process-definition/list-paging` | GET | ❌ 不推荐 |
| 查询工作流列表（旧） | `/projects/{projectCode}/process-definition/list` | GET | ⚠️ 返回部分数据 |
| 查询工作流详情 | `/projects/{projectCode}/process-definition/{code}` | GET | 待验证 |
| 查询工作流任务列表 | `/projects/{projectCode}/process-definition/query-task-definition-list?processDefinitionCode={code}` | GET | ✅ 可用 |

**示例：**
```powershell
# 查询项目下所有工作流
Invoke-RestMethod -Uri "$baseUrl/projects/158514956085248/process-definition/query-process-definition-list" -Method GET -Headers $headers

# 查询工作流的任务列表
Invoke-RestMethod -Uri "$baseUrl/projects/158514956085248/process-definition/query-task-definition-list?processDefinitionCode=158514958340096" -Method GET -Headers $headers
```

---

### 任务实例相关

| 功能 | API 路径 | 方法 | 状态 |
|------|----------|------|------|
| 查询任务实例列表 | `/projects/{projectCode}/task-instances/list-paging` | GET | 待验证 |
| 重跑任务实例 | `/projects/{projectCode}/task-instances/{id}/retry` | POST | 待验证 |

---

### 工作流实例相关 ⭐

| 功能 | API 路径 | 方法 | 状态 |
|------|----------|------|------|
| 启动工作流实例 | `/projects/{projectCode}/executors/start-process-instance` | POST | ✅ 可用（需要权限） |
| 重跑工作流 | `/projects/{projectCode}/executors/execute` | POST | ✅ 可用（需要权限） |
| 停止工作流 | `/projects/{projectCode}/executors/stop-process-instance` | POST | 待验证 |
| 查询实例列表 | `/projects/{projectCode}/process-instances/list-paging` | GET | ⚠️ 可能返回空 |
| 查询工作流详情 | `/projects/{projectCode}/process-definition/{code}` | GET | ✅ 可用 |

---

## 🔧 实际调用示例

### 1. 查询用户信息

```powershell
$headers = @{
    "token" = "0cad23ded0f0e942381fc9717c1581a8"
    "Content-Type" = "application/json"
}

$response = Invoke-RestMethod -Uri "http://127.0.0.1:12345/dolphinscheduler/users/get-user-info" -Method GET -Headers $headers
$response.data.userName  # 输出：jiangchuanchen
```

---

### 2. 查询项目列表

```powershell
$response = Invoke-RestMethod -Uri "http://127.0.0.1:12345/dolphinscheduler/projects?pageSize=130&pageNo=1" -Method GET -Headers $headers
$response.data.totalList | Select-Object code, name, userName, defCount
```

---

### 3. 查询工作流列表

```powershell
$projectCode = "158514956085248"  # 国内数仓 - 工作流
$response = Invoke-RestMethod -Uri "http://127.0.0.1:12345/dolphinscheduler/projects/$projectCode/process-definition/query-process-definition-list" -Method GET -Headers $headers
$response.data | Select-Object code, name, version
```

---

### 4. 查询工作流的任务列表

```powershell
$projectCode = "158514956085248"
$processCode = "158514958340096"  # test 工作流

$response = Invoke-RestMethod -Uri "http://127.0.0.1:12345/dolphinscheduler/projects/$projectCode/process-definition/query-task-definition-list?processDefinitionCode=$processCode" -Method GET -Headers $headers
$response.data.taskDefinitionList | Select-Object code, name, taskType, version
```

---

### 4.1 查询工作流详情

```powershell
$projectCode = "159737550740160"
$processCode = "161876531088065"  # market_fee_by_channel

$response = Invoke-RestMethod -Uri "http://127.0.0.1:12345/dolphinscheduler/projects/$projectCode/process-definition/$processCode" -Method GET -Headers $headers

# 检查工作流状态
$response.data.processDefinition.releaseState  # ONLINE = 已发布，OFFLINE = 未发布

# 查看任务定义
$response.data.taskDefinitionList | Select-Object code, name, taskType
```

---

### 5. 启动工作流实例 ⭐

```powershell
$projectCode = "159737550740160"  # okr_ads 项目
$processCode = "161876531088065"  # market_fee_by_channel 工作流

$headers = @{
    "token" = "0cad23ded0f0e942381fc9717c1581a8"
    "Content-Type" = "application/json"
}

$body = @{
    processDefinitionCode = $processCode
    startNodes = @()
    complementMode = 0
    scheduleTime = ""
    failureStrategy = 0
    warningType = 0
    warningGroupId = 0
    receivers = ""
    receiversCc = ""
    execType = 0
    taskDependType = 0
    dryRun = 0
    startParams = @{}
} | ConvertTo-Json -Depth 5

$response = Invoke-RestMethod -Uri "http://127.0.0.1:12345/dolphinscheduler/projects/$projectCode/executors/start-process-instance" -Method POST -Headers $headers -Body $body
$response

# 成功响应示例：
# {
#     "code": 0,
#     "msg": "success",
#     "data": {
#         "processInstanceId": 12345,
#         "processDefinitionCode": 161876531088065
#     }
# }
```

**错误码说明：**

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 50014 | 启动工作流实例错误 | 🔴 **常见原因：任务使用的环境配置不存在**。检查工作流任务的 `environmentCode` 是否存在。使用 `/environment/list-paging` 查询可用环境 |
| 50015 | 执行工作流实例错误 | 检查工作流是否已发布、任务配置是否正确 |
| 10109 | 查询工作流详情错误 | 确认项目 Code 和工作流 Code 正确 |
| 1200009 | 环境配置不存在 | 任务使用的环境 Code 无效，需要更新工作流任务配置或创建环境 |

**注意事项：**

1. **工作流必须已发布**（releaseState: ONLINE）⭐
2. **用户需要有项目权限**（当前用户 jiangchuanchen 是项目创建者，应该有权限）
3. **数据库连接正常**（SQL 任务需要数据源可用）
4. **Worker 组可用**（默认使用 "default" Worker 组）
5. **任务环境配置必须存在** ⭐⭐⭐ **重要！**
   - 任务的 `environmentCode` 必须是已存在的环境
   - 可用环境查询：`GET /environment/list-paging`
   - 如果环境不存在，API 启动会返回 50014 错误
   - **解决方案**：在 Web UI 中编辑工作流任务，将环境改为存在的环境（如 `global`）

---

## ⚠️ 环境配置检查清单

在调用启动 API 前，请确认：

```powershell
# 1. 查询工作流任务的环境配置
$response = Invoke-RestMethod -Uri "$baseUrl/projects/$projectCode/process-definition/$processCode" -Method GET -Headers $headers
$taskEnvCode = $response.data.taskDefinitionList[0].environmentCode
Write-Host "任务环境 Code: $taskEnvCode"

# 2. 查询可用环境列表
$envResponse = Invoke-RestMethod -Uri "$baseUrl/environment/list-paging?pageNo=1&pageSize=10" -Method GET -Headers $headers
$availableEnvs = $envResponse.data.totalList | ForEach-Object { $_.code }
Write-Host "可用环境 Code: $($availableEnvs -join ', ')"

# 3. 检查环境是否存在
if ($taskEnvCode -notin $availableEnvs) {
    Write-Host "❌ 任务使用的环境不存在！请在 Web UI 中修改任务环境配置" -ForegroundColor Red
} else {
    Write-Host "✅ 环境配置正确" -ForegroundColor Green
}
```

**推荐做法：**
- 新创建工作流时，选择 `global` 环境（最通用）
- 或根据实际需求选择 `prod` / `develop`
- 避免使用不存在的环境 Code

---

## ⚠️ 常见问题

### 问题 1：API 返回 HTML 而不是 JSON

**现象：**
```json
"<!-- Licensed to the Apache Software Foundation... -->"
```

**原因：** API 路径不正确，返回了前端页面

**解决：** 检查 API 路径，使用 Swagger UI 确认正确路径

---

### 问题 2：错误码 10109

**现象：**
```json
{"code": 10109, "msg": "query detail of process definition error"}
```

**原因：** 使用了错误的 API 路径（如 `list-paging`）

**解决：** 使用 `query-process-definition-list` 替代

---

### 问题 3：中文乱码

**现象：** 工作流名称显示为 `?????‌-??‌????`

**原因：** 数据库或 API 响应编码问题

**解决：** 
- 使用 Code 而不是名称识别工作流
- 在 Web UI 查看中文名称
- 导出 CSV 记录 Code 和名称对应关系

---

### 问题 4：项目找不到（错误 10018）

**现象：**
```json
{"code": 10018, "msg": "project not found"}
```

**原因：** 使用了项目 ID 而不是项目 Code

**解决：** 
- 项目 ID：数据库主键（如 `127`）
- 项目 Code：业务唯一标识（如 `158514956085248`）
- API 通常使用 **项目 Code**

---

## 📊 快速参考表

### 项目 Code 速查

| 项目名称 | 项目 Code | 创建者 |
|----------|-----------|--------|
| 国内数仓 - 工作流 | 158514956085248 | develop |
| okr_ads | 159737550740160 | jiangchuanchen |

### 常用工作流 Code

| 工作流名称 | 工作流 Code | 项目 Code |
|-----------|-------------|-----------|
| test | 158514958340096 | 158514956085248 |
| DWD | 158514956979200 | 158514956085248 |
| DWS | 158514957779968 | 158514956085248 |

---

## 🔗 参考链接

- Swagger UI: http://127.0.0.1:12345/dolphinscheduler/swagger-ui/index.html
- 官方文档：https://dolphinscheduler.apache.org/en-us/docs/latest

---

## 🧪 实际测试记录

### 测试：启动 market_fee_by_channel 工作流

**时间：** 2026-03-17 15:02

**工作流信息：**

```
项目 Code: 159737550740160 (okr_ads)
工作流 Code: 161876531088065 (market_fee_by_channel)
版本：3
状态：ONLINE
任务类型：SQL (StarRocks)
```

**API 调用：**

```powershell
POST /dolphinscheduler/projects/159737550740160/executors/start-process-instance
Body: {"processDefinitionCode": 161876531088065, ...}
```

**结果：** ❌ 失败

**错误响应：**
```json
{
    "code": 50014,
    "msg": "start process instance error"
}
```

**分析：**

✅ **手动启动正常** - 说明工作流配置、数据源、Worker 组都正常

❌ **API 启动失败** - 可能是 Token 权限验证问题

**可能原因：**

1. ⚠️ **Token 权限问题** - 当前 Token 可能没有足够的项目执行权限
2. ⚠️ **API 调用参数不完整** - 某些必填参数可能缺失
3. ⚠️ **会话验证** - API 可能需要额外的会话验证

**解决方案：**

1. ✅ **推荐**：在 Web UI 手动启动工作流
2. ⚠️ **尝试**：使用项目创建者的 Token（当前用户是 jiangchuanchen，应该是创建者）
3. ⚠️ **检查**：DolphinScheduler 服务端日志，查看详细错误信息
4. ⚠️ **联系管理员**：确认 API 调用权限配置

**API 调用示例（供参考）：**

```powershell
$projectCode = "159737550740160"
$processCode = "161876531088065"

$body = @{
    processDefinitionCode = $processCode
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:12345/dolphinscheduler/projects/$projectCode/executors/start-process-instance" -Method POST -Headers $headers -Body $body
```

---

## 🔧 故障排查

### 错误 50014：启动工作流实例错误

**排查步骤：**

1. **检查工作流状态**
   ```powershell
   $response = Invoke-RestMethod -Uri "$baseUrl/projects/$projectCode/process-definition/$processCode" -Method GET -Headers $headers
   $response.data.processDefinition.releaseState  # 应该是 ONLINE
   ```

2. **检查任务环境配置** ⭐
   ```powershell
   # 获取任务的环境 Code
   $taskEnvCode = $response.data.taskDefinitionList[0].environmentCode
   
   # 检查环境是否存在
   $envResponse = Invoke-RestMethod -Uri "$baseUrl/environment/query-by-code?environmentCode=$taskEnvCode" -Method GET -Headers $headers
   
   # 如果返回 1200009，说明环境不存在
   ```

3. **查询可用环境列表**
   ```powershell
   $response = Invoke-RestMethod -Uri "$baseUrl/environment/list-paging?pageNo=1&pageSize=10" -Method GET -Headers $headers
   $response.data.totalList | Select-Object code, name
   ```

4. **检查 Worker 组**
   ```powershell
   $response = Invoke-RestMethod -Uri "$baseUrl/worker-groups" -Method GET -Headers $headers
   ```

**实际案例：**

```
项目：okr_ads (159737550740160)
工作流：market_fee_by_channel (161876531088065)
错误：50014

根本原因：
- 任务使用的环境 Code: 15843695995616
- 该环境不存在（返回错误 1200009）
- 可用环境：prod(154818922491872), develop(154818735899616), global(154818709784544)

解决方案：
- 在 Web UI 中编辑工作流任务
- 将环境改为存在的环境 Code
- 保存并发布工作流
```

---

## 📝 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.3 | 2026-03-17 | 添加错误 50014 排查步骤和环境配置检查 |
| v1.2 | 2026-03-17 | 添加启动工作流测试记录和错误码说明 |
| v1.1 | 2026-03-17 | 添加实际调用示例和常见问题 |
| v1.0 | 2026-03-17 | 初始版本 |
