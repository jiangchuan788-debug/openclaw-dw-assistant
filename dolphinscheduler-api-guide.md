# DolphinScheduler API 操作手册

> 版本：v1.0 (2026-03-17)  
> 目标地址：http://127.0.0.1:12345/dolphinscheduler

---

## 📋 目录

1. [API 认证](#api-认证)
2. [工作流管理](#工作流管理)
3. [任务管理](#任务管理)
4. [项目管理](#项目管理)
5. [常用 API 列表](#常用 api 列表)

---

## 🔐 API 认证

### 方式一：令牌管理（推荐）⭐

**适用场景：** API 调用、自动化脚本

**获取 Token 步骤：**

1. 登录调度系统 Web UI
2. 点击 **安全中心** → **令牌管理**
3. 点击 **创建令牌**
4. 选择 **失效时间**（Token 有效期）
5. 选择 **用户**（以指定用户执行接口操作）
6. 点击 **生成令牌**，拷贝 Token 字符串
7. 点击 **提交**

**使用 Token：**

所有 API 请求需要在 Header 中携带 Token：

```
token: <你的 Token>
Content-Type: application/json
```

---

### 方式二：用户名密码登录

**接口：** `POST /dolphinscheduler/login`

**请求体：**
```json
{
  "userName": "your_username",
  "userPassword": "your_password"
}
```

**响应示例：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "userInfo": {
      "id": 1,
      "userName": "admin",
      "email": "admin@example.com"
    }
  }
}
```

**注意：** 此方式获取的 Token 可能有有效期限制，推荐使用方法一的持久令牌。

---

## 📁 项目管理

### 列出所有项目

**接口：** `GET /dolphinscheduler/projects`

**参数：**
- `pageNo` - 页码（默认 1）
- `pageSize` - 每页数量（默认 10）
- `searchVal` - 搜索关键词（可选）

**响应示例：**
```json
{
  "code": 0,
  "data": {
    "totalList": [
      {
        "code": 10001,
        "name": "project-name",
        "description": "项目描述"
      }
    ]
  }
}
```

### 创建项目

**接口：** `POST /dolphinscheduler/projects`

**请求体：**
```json
{
  "name": "my-project",
  "description": "项目描述"
}
```

---

## 🔄 工作流管理（Workflow/Process Definition）

### 列出工作流定义 ✅

**接口：** `GET /dolphinscheduler/projects/{projectCode}/process-definition/query-process-definition-list`

**参数：** 无

**响应示例：**
```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "code": 158514956979200,
      "name": "DWD",
      "version": 66
    }
  ]
}
```

---

### 查询工作流定义列表（分页）⚠️

**接口：** `GET /dolphinscheduler/projects/{projectCode}/process-definition/list-paging`

**注意：** 此接口在某些版本中可能返回错误，推荐使用上面的 `query-process-definition-list`

### 创建工作流

**接口：** `POST /dolphinscheduler/projects/{projectCode}/process-definitions`

**请求体：**
```json
{
  "name": "workflow-name",
  "description": "工作流描述",
  "locations": {},
  "taskDefinitionJson": "[...]",
  "taskRelationJson": "[...]",
  "timeout": 0
}
```

### 启动工作流实例

**接口：** `POST /dolphinscheduler/projects/{projectCode}/executors/start-process-instance`

**请求体：**
```json
{
  "processDefinitionCode": 1234567890,
  "startNodes": [],
  "complementMode": 0,
  "scheduleTime": "",
  "failureStrategy": 0,
  "warningType": 0,
  "warningGroupId": 0,
  "receivers": "",
  "receiversCc": "",
  "execType": 0,
  "taskDependType": 0,
  "dryRun": 0,
  "startParams": {}
}
```

### 停止工作流实例

**接口：** `POST /dolphinscheduler/projects/{projectCode}/executors/stop-process-instance`

**请求体：**
```json
{
  "processInstanceId": 12345
}
```

### 查看工作流实例状态

**接口：** `GET /dolphinscheduler/projects/{projectCode}/process-instances/{id}`

---

## 📝 任务管理

### 列出任务定义

**接口：** `GET /dolphinscheduler/projects/{projectCode}/task-definitions`

### 创建任务定义

**接口：** `POST /dolphinscheduler/projects/{projectCode}/task-definitions`

**请求体：**
```json
{
  "name": "task-name",
  "taskType": "SHELL",
  "taskParams": {
    "resourceList": [],
    "localParams": [],
    "rawScript": "echo 'Hello World'"
  },
  "flag": 1,
  "taskPriority": "MEDIUM",
  "workerGroup": "default",
  "failRetryTimes": 0,
  "failRetryInterval": 1,
  "timeoutFlag": "CLOSE",
  "timeoutNotifyStrategy": "",
  "timeout": 0
}
```

---

## 🔧 常用 API 列表

| 功能 | 方法 | 接口路径 |
|------|------|----------|
| 登录 | POST | `/dolphinscheduler/login` |
| 登出 | POST | `/dolphinscheduler/logout` |
| 获取用户信息 | GET | `/dolphinscheduler/users/get-user-info` |
| 列出项目 | GET | `/dolphinscheduler/projects` |
| 创建项目 | POST | `/dolphinscheduler/projects` |
| 列出工作流 | GET | `/dolphinscheduler/projects/{projectCode}/process-definitions` |
| 创建工作流 | POST | `/dolphinscheduler/projects/{projectCode}/process-definitions` |
| 启动工作流 | POST | `/dolphinscheduler/projects/{projectCode}/executors/start-process-instance` |
| 停止工作流 | POST | `/dolphinscheduler/projects/{projectCode}/executors/stop-process-instance` |
| 列出任务 | GET | `/dolphinscheduler/projects/{projectCode}/task-definitions` |
| 创建任务 | POST | `/dolphinscheduler/projects/{projectCode}/task-definitions` |

---

## 📊 状态码说明

| Code | 说明 |
|------|------|
| 0 | 成功 |
| 非 0 | 失败（具体错误信息在 msg 字段） |

---

## 🔗 参考链接

- 官方文档：https://dolphinscheduler.apache.org/en-us/docs/latest
- API 源码：https://github.com/apache/dolphinscheduler

---

## 📝 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.1 | 2026-03-17 | 添加实际 API 测试用例和响应示例 |
| v1.0 | 2026-03-17 | 初始版本，基础 API 整理 |

---

## ✅ 实际测试记录

### 测试环境

| 项目 | 值 |
|------|-----|
| API 地址 | `http://127.0.0.1:12345` |
| 用户名 | `jiangchuanchen` |
| 用户类型 | `ADMIN_USER` |
| Token | `0cad23ded0f0e942381fc9717c1581a8` |
| 测试时间 | 2026-03-17 14:03 |

### 测试 1：获取用户信息 ✅

**请求：**
```bash
GET http://127.0.0.1:12345/dolphinscheduler/users/get-user-info
Headers: token=0cad23ded0f0e942381fc9717c1581a8
```

**响应：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "id": 69,
    "userName": "jiangchuanchen",
    "email": "jiangchuanchen@kn.group",
    "userType": "ADMIN_USER",
    "tenantCode": "dolphinscheduler",
    "state": 1,
    "timeZone": "Asia/Shanghai"
  }
}
```

### 测试 2：查询项目列表 ✅

**请求：**
```bash
GET http://127.0.0.1:12345/dolphinscheduler/projects?pageSize=10&pageNo=1
Headers: token=0cad23ded0f0e942381fc9717c1581a8
```

**响应摘要：**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "total": 130,
    "totalPage": 13,
    "pageSize": 10,
    "totalList": [
      {
        "code": 164464452424384,
        "name": "...",
        "defCount": 13,
        "instRunningCount": 0
      }
    ]
  }
}
```

**结论：** 当前用户有 130 个项目，分布在 13 页

### 常见问题

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 10049 | 登录用户查询项目列表错误 | 检查 Token 权限或添加分页参数 |
