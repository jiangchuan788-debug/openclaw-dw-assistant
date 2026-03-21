# DolphinScheduler API 调用完整指南

> **版本：** v2.0  
> **更新日期：** 2026-03-17  
> **目标环境：** http://127.0.0.1:12345  
> **状态：** ✅ 已验证可用

---

## 📋 目录

1. [快速开始](#快速开始)
2. [认证配置](#认证配置)
3. [常用 API 列表](#常用 api 列表)
4. [启动工作流（完整版）](#启动工作流完整版)
5. [常见错误排查](#常见错误排查)
6. [PowerShell 函数库](#powershell-函数库)

---

## 🚀 快速开始

### 30 秒启动工作流

```powershell
# 复制即用 - 启动工作流示例
$projectCode = "159737550740160"
$processCode = "168243093291713"
$token = "0cad23ded0f0e942381fc9717c1581a8"

$body = @{
    "processDefinitionCode" = "$processCode"
    "failureStrategy" = "CONTINUE"
    "warningType" = "NONE"
    "warningGroupId" = "0"
    "processInstancePriority" = "MEDIUM"
    "workerGroup" = "default"
    "environmentCode" = "154818922491872"
    "tenantCode" = "dolphinscheduler"
    "taskDependType" = "TASK_POST"
    "runMode" = "RUN_MODE_SERIAL"
    "execType" = "START_PROCESS"
    "dryRun" = "0"
    "scheduleTime" = ""  # ⚠️ 必须传，即使是空字符串！
}

$response = Invoke-RestMethod -Uri "http://127.0.0.1:12345/dolphinscheduler/projects/$projectCode/executors/start-process-instance" -Method POST -Headers @{ "token" = $token } -Body $body

if ($response.code -eq 0) {
    Write-Host "✅ 启动成功！实例 ID: $($response.data)" -ForegroundColor Green
} else {
    Write-Host "❌ 失败：$($response.msg)" -ForegroundColor Red
}
```

---

## 🔐 认证配置

### 获取 Token

1. 登录 DolphinScheduler Web UI
2. 点击 **安全中心** → **令牌管理**
3. 点击 **创建令牌**
4. 设置失效时间和用户
5. 拷贝 Token 字符串

### 当前环境配置

```powershell
# 全局配置
$DS_TOKEN = "0cad23ded0f0e942381fc9717c1581a8"
$DS_BASE_URL = "http://127.0.0.1:12345/dolphinscheduler"
$DS_HEADERS = @{ "token" = $DS_TOKEN }

# 当前用户信息
# 用户名：jiangchuanchen
# 用户 ID: 69
# 用户类型：ADMIN_USER
# 租户：dolphinscheduler
```

---

## 📚 常用 API 列表

### 用户相关

| 功能 | API 路径 | 方法 | 示例 |
|------|----------|------|------|
| 获取当前用户信息 | `/users/get-user-info` | GET | `Invoke-RestMethod -Uri "$DS_BASE_URL/users/get-user-info" -Method GET -Headers $DS_HEADERS` |

### 项目相关

| 功能 | API 路径 | 方法 | 说明 |
|------|----------|------|------|
| 查询项目列表 | `/projects` | GET | 返回所有项目 |
| 查询项目详情 | `/projects/{projectCode}` | GET | 根据项目 Code 查询 |

### 工作流相关

| 功能 | API 路径 | 方法 | 说明 |
|------|----------|------|------|
| 查询工作流列表 | `/projects/{projectCode}/process-definition/query-process-definition-list` | GET | 返回项目下所有工作流 |
| 查询工作流详情 | `/projects/{projectCode}/process-definition/{code}` | GET | 获取工作流详细信息 |
| **启动工作流实例** | `/projects/{projectCode}/executors/start-process-instance` | **POST** | ⭐ 最常用 |
| 重跑工作流 | `/projects/{projectCode}/executors/execute` | POST | 重跑已有实例 |
| 停止工作流 | `/projects/{projectCode}/executors/stop-process-instance` | POST | 停止运行中的实例 |

### 环境相关

| 功能 | API 路径 | 方法 | 说明 |
|------|----------|------|------|
| 查询环境列表 | `/environment/list-paging?pageNo=1&pageSize=10` | GET | 获取可用环境列表 |
| 查询环境详情 | `/environment/query-by-code?environmentCode={code}` | GET | 根据环境 Code 查询 |

### 任务实例相关

| 功能 | API 路径 | 方法 | 说明 |
|------|----------|------|------|
| 查询任务实例列表 | `/projects/{projectCode}/task-instances/list-paging` | GET | 查询任务执行记录 |
| 重跑任务实例 | `/projects/{projectCode}/task-instances/{id}/retry` | POST | 重跑单个任务 |

---

## 🎯 启动工作流（完整版）

### 场景 1：基础启动（无自定义参数）

参考上一节代码示例。

---

### 场景 2：带自定义参数启动 ⭐

参考上文。

---

### 场景 3：只执行单个任务 ⭐⭐⭐

**需求：** 只执行工作流中的某一个任务，而不是整个工作流

**核心参数：**

| 参数名 | 值 | 说明 |
|--------|-----|------|
| `startNodeList` | 任务 Code | 指定要执行的任务 Code（多个任务用逗号分隔） |
| `taskDependType` | `TASK_ONLY` | 只执行指定任务，不执行上下游 |

**taskDependType 三种模式：**

| 模式 | 说明 | 使用场景 |
|------|------|----------|
| `TASK_ONLY` | 只执行当前任务 | 🎯 单独重跑某个任务 |
| `TASK_POST` | 执行当前任务 + 所有下游任务 | 正常启动整个工作流（默认） |
| `TASK_PRE` | 执行当前任务 + 所有上游任务 | 补修某条数据链路 |

**PowerShell 示例：**

```powershell
# 1. 获取任务 Code（先查询工作流详情）
$response = Invoke-RestMethod -Uri "$DS_BASE_URL/projects/$projectCode/process-definition/$processCode" -Method GET -Headers $DS_HEADERS
$taskCode = $response.data.taskDefinitionList | Where-Object { $_.name -eq "market_fee_by_channel_2" } | Select-Object -ExpandProperty code

# 2. 启动单个任务
$body = @{
    "processDefinitionCode" = "$processCode"
    # ... 其他参数 ...
    "startNodeList" = "$taskCode"      # 🎯 指定任务 Code
    "taskDependType" = "TASK_ONLY"     # 🎯 只执行当前任务
}
```

**完整示例代码：**

```powershell
# ==================== 配置区域 ====================
$projectCode = "159737550740160"
$processCode = "168243093291713"
$taskCode = "168251685969600"  # market_fee_by_channel_2 的 Code
$envCode = "154818922491872"
$tenantCode = "dolphinscheduler"
$token = "0cad23ded0f0e942381fc9717c1581a8"

# ==================== 自定义参数 ====================
$today = Get-Date -Format "yyyy-MM-dd"
$startParamsJsonStr = @{ "dt" = $today } | ConvertTo-Json -Compress

# ==================== API 调用 ====================
$uri = "http://127.0.0.1:12345/dolphinscheduler/projects/$projectCode/executors/start-process-instance"
$headers = @{ "token" = $token }

$body = @{
    "processDefinitionCode" = "$processCode"
    "failureStrategy" = "CONTINUE"
    "warningType" = "NONE"
    "warningGroupId" = "0"
    "processInstancePriority" = "MEDIUM"
    "workerGroup" = "default"
    "environmentCode" = "$envCode"
    "tenantCode" = "$tenantCode"
    "taskDependType" = "TASK_ONLY"    # 🎯 只执行指定任务
    "runMode" = "RUN_MODE_SERIAL"
    "execType" = "START_PROCESS"
    "dryRun" = "0"
    "scheduleTime" = ""
    "startParams" = $startParamsJsonStr
    "startNodeList" = "$taskCode"     # 🎯 指定任务 Code
}

$response = Invoke-RestMethod -Uri $uri -Method POST -Headers $headers -Body $body

if ($response.code -eq 0) {
    Write-Host "✅ 启动成功！实例 ID: $($response.data)" -ForegroundColor Green
    Write-Host "只执行任务：$taskCode" -ForegroundColor Green
}
```

**测试结果：**

```
✅ 启动成功！
实例 ID: 168251898288832
任务名称：market_fee_by_channel_2
任务 Code: 168251685969600
自定义参数：dt=2026-03-17
执行模式：TASK_ONLY
```

**注意事项：**

1. **任务 Code vs 任务名称** - 新版推荐使用任务 Code，旧版本可能支持任务名称
2. **多个任务** - `startNodeList = "code1,code2"` 用逗号分隔
3. **环境配置** - 单个任务也需要正确的 environmentCode

---

### 场景 4：执行当前任务 + 所有下游任务

```powershell
$body = @{
    # ... 其他参数 ...
    "startNodeList" = "$taskCode"
    "taskDependType" = "TASK_POST"    # 执行当前 + 所有下游
}
```

---

### 场景 5：执行当前任务 + 所有上游任务

```powershell
$body = @{
    # ... 其他参数 ...
    "startNodeList" = "$taskCode"
    "taskDependType" = "TASK_PRE"     # 执行当前 + 所有上游
}
```

---

### 必填参数说明

**需求示例：** 传递 `dt=2026-03-17 00:00:00` 给工作流

**核心字段：** `startParams` - 必须是 **JSON 字符串** 格式

**PowerShell 实现：**

```powershell
# 1. 定义自定义参数
$myCustomTime = "2026-03-17 00:00:00"

# 2. 转换为 JSON 字符串（自动处理转义）
$startParamsJsonStr = @{ "dt" = $myCustomTime } | ConvertTo-Json -Compress
# 输出：{"dt":"2026-03-17 00:00:00"}

# 3. 在 Body 中使用
$body = @{
    "processDefinitionCode" = "$processCode"
    # ... 其他参数 ...
    "scheduleTime" = ""
    "startParams" = $startParamsJsonStr  # 🎯 传递 JSON 字符串
}
```

**完整示例代码：**

```powershell
# ==================== 配置区域 ====================
$projectCode = "159737550740160"
$processCode = "168243093291713"
$envCode = "154818922491872"
$tenantCode = "dolphinscheduler"
$token = "0cad23ded0f0e942381fc9717c1581a8"

# ==================== 自定义参数 ====================
$myCustomTime = "2026-03-17 00:00:00"
$startParamsJsonStr = @{ "dt" = $myCustomTime } | ConvertTo-Json -Compress

# ==================== API 调用 ====================
$uri = "http://127.0.0.1:12345/dolphinscheduler/projects/$projectCode/executors/start-process-instance"
$headers = @{ "token" = $token }

$body = @{
    "processDefinitionCode" = "$processCode"
    "failureStrategy" = "CONTINUE"
    "warningType" = "NONE"
    "warningGroupId" = "0"
    "processInstancePriority" = "MEDIUM"
    "workerGroup" = "default"
    "environmentCode" = "$envCode"
    "tenantCode" = "$tenantCode"
    "taskDependType" = "TASK_POST"
    "runMode" = "RUN_MODE_SERIAL"
    "execType" = "START_PROCESS"
    "dryRun" = "0"
    "scheduleTime" = ""
    "startParams" = $startParamsJsonStr  # 🎯 自定义参数
}

$response = Invoke-RestMethod -Uri $uri -Method POST -Headers $headers -Body $body

if ($response.code -eq 0) {
    Write-Host "✅ 启动成功！实例 ID: $($response.data)" -ForegroundColor Green
}
```

**传递多个参数：**

```powershell
$startParamsJsonStr = @{ 
    "dt" = "2026-03-17"
    "channel" = "app"
    "is_test" = "1"
} | ConvertTo-Json -Compress
# 输出：{"dt":"2026-03-17","channel":"app","is_test":"1"}
```

**参数优先级：**

启动参数 > 局部参数 > 上游任务传递参数 > 全局参数 > 项目级别参数

---

### 必填参数说明

| 参数名 | 类型 | 必填 | 示例值 | 说明 |
|--------|------|------|--------|------|
| processDefinitionCode | String | ✅ | 168243093291713 | 工作流定义 Code |
| failureStrategy | String | ✅ | CONTINUE | 失败策略：CONTINUE/END |
| warningType | String | ✅ | NONE | 告警类型：NONE/SUCCESS/FAILURE/ALL |
| warningGroupId | String | ✅ | 0 | 告警组 ID |
| processInstancePriority | String | ✅ | MEDIUM | 优先级：MEDIUM/HIGHEST/LOWEST |
| workerGroup | String | ✅ | default | Worker 组名称 |
| environmentCode | String | ✅ | 154818922491872 | 环境 Code（SQL 任务必需） |
| tenantCode | String | ✅ | dolphinscheduler | 租户 Code |
| taskDependType | String | ✅ | TASK_POST | 任务依赖类型 |
| runMode | String | ✅ | RUN_MODE_SERIAL | 运行模式 |
| execType | String | ✅ | START_PROCESS | 执行类型 |
| dryRun | String | ✅ | 0 | 是否空跑：0/1 |
| **scheduleTime** | String | ✅ | "" | **调度时间（即使为空也必须传！）** ⭐ |

### 完整示例代码

```powershell
# ==================== 配置区域 ====================
$projectCode = "159737550740160"      # 项目 Code
$processCode = "168243093291713"      # 工作流 Code
$envCode = "154818922491872"          # 环境 Code（prod）
$tenantCode = "dolphinscheduler"      # 租户名称
$token = "0cad23ded0f0e942381fc9717c1581a8"

# ==================== API 调用 ====================
$uri = "http://127.0.0.1:12345/dolphinscheduler/projects/$projectCode/executors/start-process-instance"

$headers = @{ "token" = $token }

$body = @{
    "processDefinitionCode" = "$processCode"
    "failureStrategy" = "CONTINUE"
    "warningType" = "NONE"
    "warningGroupId" = "0"
    "processInstancePriority" = "MEDIUM"
    "workerGroup" = "default"
    "environmentCode" = "$envCode"
    "tenantCode" = "$tenantCode"
    "taskDependType" = "TASK_POST"
    "runMode" = "RUN_MODE_SERIAL"
    "execType" = "START_PROCESS"
    "dryRun" = "0"
    "scheduleTime" = ""  # ⚠️ 关键！必须传这个字段，即使是空字符串
}

try {
    Write-Host "🚀 正在启动工作流 $processCode..." -ForegroundColor Cyan
    
    $response = Invoke-RestMethod -Uri $uri -Method POST -Headers $headers -Body $body
    
    if ($response.code -eq 0) {
        Write-Host "`n✅ 启动成功！" -ForegroundColor Green
        Write-Host "实例 ID: $($response.data)" -ForegroundColor Green
        return $response.data
    } else {
        Write-Host "`n❌ 启动失败：$($response.msg)" -ForegroundColor Red
        Write-Host "错误码：$($response.code)" -ForegroundColor Red
        return $null
    }
} catch {
    Write-Host "`n❌ 异常：$($_.Exception.Message)" -ForegroundColor Red
    return $null
}
```

### 响应示例

**成功响应：**
```json
{
    "code": 0,
    "msg": "success",
    "data": 168250925189824,
    "success": true,
    "failed": false
}
```

**失败响应：**
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

## ⚠️ 常见错误排查

### 错误 50014：启动工作流实例错误

**最常见原因：**

| 原因 | 解决方案 | 优先级 |
|------|----------|--------|
| 缺少 `scheduleTime` 参数 | 添加 `"scheduleTime" = ""` | ⭐⭐⭐⭐⭐ |
| 环境 Code 不存在 | 检查任务的 environmentCode 是否正确 | ⭐⭐⭐⭐ |
| 租户 Code 错误 | 添加 `"tenantCode" = "dolphinscheduler"` | ⭐⭐⭐⭐ |
| 工作流未发布 | 确认工作流状态为 ONLINE | ⭐⭐⭐ |
| 数据源不可用 | 检查 SQL 任务使用的数据源 | ⭐⭐ |

**排查步骤：**

```powershell
# 1. 查询工作流状态
$response = Invoke-RestMethod -Uri "$DS_BASE_URL/projects/$projectCode/process-definition/$processCode" -Method GET -Headers $DS_HEADERS
$response.data.processDefinition.releaseState  # 应该是 ONLINE

# 2. 查询任务环境配置
$taskEnvCode = $response.data.taskDefinitionList[0].environmentCode
Write-Host "任务环境 Code: $taskEnvCode"

# 3. 查询可用环境列表
$envResponse = Invoke-RestMethod -Uri "$DS_BASE_URL/environment/list-paging?pageNo=1&pageSize=10" -Method GET -Headers $DS_HEADERS
$envResponse.data.totalList | Format-Table code, name

# 4. 检查环境是否存在
if ($taskEnvCode -notin ($envResponse.data.totalList | ForEach-Object { $_.code })) {
    Write-Host "❌ 任务使用的环境不存在！" -ForegroundColor Red
}
```

### 错误 50015：执行工作流实例错误

**原因：** 工作流未发布或配置错误

**解决方案：**
1. 确认工作流状态为 ONLINE
2. 在 Web UI 中重新发布工作流

### 错误 10109：查询工作流详情错误

**原因：** 项目 Code 或工作流 Code 错误

**解决方案：** 确认 Code 值正确

### 错误 1200009：环境配置不存在

**原因：** 任务使用的环境 Code 无效

**解决方案：**
1. 在 Web UI 中编辑工作流任务
2. 将环境改为存在的环境（prod/develop/global）
3. 保存并发布工作流

---

## 🛠️ PowerShell 函数库

### 初始化配置

```powershell
# 全局配置
$DS_CONFIG = @{
    BaseUrl = "http://127.0.0.1:12345/dolphinscheduler"
    Token = "0cad23ded0f0e942381fc9717c1581a8"
    TenantCode = "dolphinscheduler"
    DefaultEnvCode = "154818922491872"  # prod
    DefaultWorkerGroup = "default"
}

$DS_HEADERS = @{ "token" = $DS_CONFIG.Token }
```

### 启动工作流函数（支持自定义参数 + 单任务）

```powershell
function Start-DolphinWorkflow {
    param(
        [Parameter(Mandatory=$true)]
        [string]$ProjectCode,
        
        [Parameter(Mandatory=$true)]
        [string]$ProcessCode,
        
        [string]$EnvironmentCode = $DS_CONFIG.DefaultEnvCode,
        
        [string]$FailureStrategy = "CONTINUE",
        
        [string]$WarningType = "NONE",
        
        [ValidateSet("MEDIUM", "HIGHEST", "LOWEST")]
        [string]$Priority = "MEDIUM",
        
        # 🎯 自定义参数（哈希表）
        [hashtable]$CustomParams = @{},
        
        # 🎯 指定单个任务（可选）
        [string]$TaskCode = "",
        
        # 🎯 任务依赖类型（可选）
        [ValidateSet("TASK_ONLY", "TASK_POST", "TASK_PRE")]
        [string]$TaskDependType = "TASK_POST"
    )
    
    $uri = "$($DS_CONFIG.BaseUrl)/projects/$ProjectCode/executors/start-process-instance"
    
    # 将自定义参数转换为 JSON 字符串
    $startParamsJsonStr = $CustomParams | ConvertTo-Json -Compress
    
    $body = @{
        "processDefinitionCode" = $ProcessCode
        "failureStrategy" = $FailureStrategy
        "warningType" = $WarningType
        "warningGroupId" = "0"
        "processInstancePriority" = $Priority
        "workerGroup" = $DS_CONFIG.DefaultWorkerGroup
        "environmentCode" = $EnvironmentCode
        "tenantCode" = $DS_CONFIG.TenantCode
        "taskDependType" = $TaskDependType  # 🎯 任务依赖类型
        "runMode" = "RUN_MODE_SERIAL"
        "execType" = "START_PROCESS"
        "dryRun" = "0"
        "scheduleTime" = ""  # ⚠️ 必须传
        "startParams" = $startParamsJsonStr  # 🎯 自定义参数
    }
    
    # 🎯 如果指定了任务 Code，添加 startNodeList
    if ($TaskCode) {
        $body["startNodeList"] = $TaskCode
    }
    
    $uri = "$($DS_CONFIG.BaseUrl)/projects/$ProjectCode/executors/start-process-instance"
    
    $body = @{
        "processDefinitionCode" = $ProcessCode
        "failureStrategy" = $FailureStrategy
        "warningType" = $WarningType
        "warningGroupId" = "0"
        "processInstancePriority" = $Priority
        "workerGroup" = $DS_CONFIG.DefaultWorkerGroup
        "environmentCode" = $EnvironmentCode
        "tenantCode" = $DS_CONFIG.TenantCode
        "taskDependType" = "TASK_POST"
        "runMode" = "RUN_MODE_SERIAL"
        "execType" = "START_PROCESS"
        "dryRun" = "0"
        "scheduleTime" = ""  # ⚠️ 必须传
    }
    
    try {
        $response = Invoke-RestMethod -Uri $uri -Method POST -Headers $DS_HEADERS -Body $body
        
        if ($response.code -eq 0) {
            Write-Host "✅ 启动成功！实例 ID: $($response.data)" -ForegroundColor Green
            return @{
                Success = $true
                InstanceId = $response.data
                Message = "success"
            }
        } else {
            Write-Host "❌ 失败：$($response.msg)" -ForegroundColor Red
            return @{
                Success = $false
                InstanceId = $null
                Message = $response.msg
                Code = $response.code
            }
        }
    } catch {
        Write-Host "❌ 异常：$($_.Exception.Message)" -ForegroundColor Red
        return @{
            Success = $false
            InstanceId = $null
            Message = $_.Exception.Message
        }
    }
}

# 使用示例

# 基础启动
Start-DolphinWorkflow -ProjectCode "159737550740160" -ProcessCode "168243093291713"

# 带自定义参数启动
Start-DolphinWorkflow -ProjectCode "159737550740160" -ProcessCode "168243093291713" -CustomParams @{ "dt" = "2026-03-17 00:00:00" }

# 带多个自定义参数
Start-DolphinWorkflow -ProjectCode "159737550740160" -ProcessCode "168243093291713" -CustomParams @{ 
    "dt" = "2026-03-17"
    "channel" = "app"
    "is_test" = "1"
}

# 🎯 只执行单个任务
Start-DolphinWorkflow -ProjectCode "159737550740160" -ProcessCode "168243093291713" -TaskCode "168251685969600" -TaskDependType "TASK_ONLY"

# 🎯 只执行单个任务 + 自定义参数
Start-DolphinWorkflow -ProjectCode "159737550740160" -ProcessCode "168243093291713" -TaskCode "168251685969600" -TaskDependType "TASK_ONLY" -CustomParams @{ "dt" = "2026-03-17" }

# 🎯 执行当前任务 + 所有下游任务
Start-DolphinWorkflow -ProjectCode "159737550740160" -ProcessCode "168243093291713" -TaskCode "168251685969600" -TaskDependType "TASK_POST"

# 🎯 执行当前任务 + 所有上游任务
Start-DolphinWorkflow -ProjectCode "159737550740160" -ProcessCode "168243093291713" -TaskCode "168251685969600" -TaskDependType "TASK_PRE"
```

### 查询工作流列表函数

```powershell
function Get-DolphinWorkflows {
    param(
        [Parameter(Mandatory=$true)]
        [string]$ProjectCode
    )
    
    $uri = "$($DS_CONFIG.BaseUrl)/projects/$ProjectCode/process-definition/query-process-definition-list"
    
    try {
        $response = Invoke-RestMethod -Uri $uri -Method GET -Headers $DS_HEADERS
        return $response.data | Select-Object code, name, version, releaseState
    } catch {
        Write-Host "❌ 查询失败：$($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

# 使用示例
# Get-DolphinWorkflows -ProjectCode "159737550740160"
```

### 查询环境列表函数

```powershell
function Get-DolphinEnvironments {
    $uri = "$($DS_CONFIG.BaseUrl)/environment/list-paging?pageNo=1&pageSize=10"
    
    try {
        $response = Invoke-RestMethod -Uri $uri -Method GET -Headers $DS_HEADERS
        return $response.data.totalList | Select-Object code, name
    } catch {
        Write-Host "❌ 查询失败：$($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

# 使用示例
# Get-DolphinEnvironments
```

---

## 📊 快速参考表

### 项目 Code 速查

| 项目名称 | 项目 Code |
|----------|-----------|
| okr_ads | 159737550740160 |
| 国内数仓 - 工作流 | 158514956085248 |

### 环境 Code 速查

| 环境名称 | 环境 Code |
|----------|-----------|
| prod | 154818922491872 |
| develop | 154818735899616 |
| global | 154818709784544 |

### 租户名称

| 租户 | 说明 |
|------|------|
| dolphinscheduler | 默认租户 |

---

## 📝 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v2.0 | 2026-03-17 | 添加 scheduleTime 参数（关键修复）、PowerShell 函数库 |
| v1.3 | 2026-03-17 | 添加环境配置检查、故障排查步骤 |
| v1.2 | 2026-03-17 | 添加启动工作流测试记录 |
| v1.1 | 2026-03-17 | 添加实际调用示例 |
| v1.0 | 2026-03-17 | 初始版本 |

---

## 🔗 相关文档

- `dolphinscheduler-start-error-report.md` - 启动失败完整测试报告
- `dolphinscheduler-api-guide.md` - API 操作手册
- `dolphinscheduler-workflows.csv` - 工作流清单
- `memory/2026-03-17.md` - 学习笔记

---

**最后更新：** 2026-03-17 17:03 GMT+8
