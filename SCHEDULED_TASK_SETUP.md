# 定时任务配置指南

> **目的：** 配置每天 22:00 自动生成每日总结  
> **创建日期：** 2026-03-17

---

## 📋 已创建的文件

| 文件名 | 说明 |
|--------|------|
| `daily_summary.py` | 每日总结生成脚本 |
| `memory/daily-summary-YYYY-MM-DD.md` | 每日总结文件（每天自动生成） |

---

## ⚙️ 配置定时任务

### 方式 1：Windows 任务计划程序（推荐）

#### 步骤 1：打开任务计划程序
1. 按 `Win + R`
2. 输入 `taskschd.msc`
3. 按回车

#### 步骤 2：创建基本任务
1. 点击右侧 **"创建基本任务..."**
2. 名称：`OpenClaw 每日总结`
3. 描述：`每天晚上 22:00 自动生成当日工作总结`
4. 点击 **"下一步"**

#### 步骤 3：设置触发器
1. 选择 **"每天"**
2. 点击 **"下一步"**
3. 设置开始时间：`22:00:00`
4. 重复周期：`1` 天
5. 点击 **"下一步"**

#### 步骤 4：设置操作
1. 选择 **"启动程序"**
2. 点击 **"下一步"**
3. 填写：
   - **程序/脚本：** `python`
   - **添加参数：** `C:\Users\21326\.openclaw\workspace\daily_summary.py`
   - **起始于：** `C:\Users\21326\.openclaw\workspace`
4. 点击 **"下一步"**

#### 步骤 5：完成配置
1. 勾选 **"当单击完成时，打开此任务属性的对话框"**
2. 点击 **"完成"**

#### 步骤 6：高级设置
1. 切换到 **"条件"** 选项卡
2. 取消勾选 **"只有在计算机使用交流电源时才启动此任务"**（笔记本需要）
3. 切换到 **"设置"** 选项卡
4. 勾选 **"如果错过计划开始时间，立即启动任务"**
5. 点击 **"确定"**

---

### 方式 2：使用 schtasks 命令

以管理员身份打开命令提示符，执行：

```cmd
schtasks /Create /TN "OpenClaw 每日总结" /TR "python C:\Users\21326\.openclaw\workspace\daily_summary.py" /SC DAILY /ST 22:00 /RL HIGHEST /F
```

**参数说明：**
- `/TN` - 任务名称
- `/TR` - 要运行的程序
- `/SC` - 计划频率（DAILY=每天）
- `/ST` - 开始时间
- `/RL` - 运行级别（HIGHEST=最高权限）
- `/F` - 强制创建

**验证任务：**
```cmd
schtasks /Query /TN "OpenClaw 每日总结"
```

**删除任务：**
```cmd
schtasks /Delete /TN "OpenClaw 每日总结" /F
```

---

### 方式 3：使用 PowerShell

以管理员身份打开 PowerShell，执行：

```powershell
$taskName = "OpenClaw 每日总结"
$scriptPath = "C:\Users\21326\.openclaw\workspace\daily_summary.py"
$workingDir = "C:\Users\21326\.openclaw\workspace"

# 创建任务操作
$action = New-ScheduledTaskAction -Execute "python" -Argument $scriptPath -WorkingDirectory $workingDir

# 创建触发器（每天 22:00）
$trigger = New-ScheduledTaskTrigger -Daily -At 22:00

# 创建任务
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Description "每天晚上 22:00 自动生成每日总结" -RunLevel Highest -Force

Write-Host "✅ 定时任务已创建：$taskName"
```

**验证任务：**
```powershell
Get-ScheduledTask -TaskName "OpenClaw 每日总结"
```

**启用任务：**
```powershell
Enable-ScheduledTask -TaskName "OpenClaw 每日总结"
```

**禁用任务：**
```powershell
Disable-ScheduledTask -TaskName "OpenClaw 每日总结"
```

**删除任务：**
```powershell
Unregister-ScheduledTask -TaskName "OpenClaw 每日总结" -Confirm:$false
```

---

## 🧪 测试脚本

### 手动执行测试

```bash
# 方式 1：直接运行
cd C:\Users\21326\.openclaw\workspace
python daily_summary.py

# 方式 2：使用完整路径
python C:\Users\21326\.openclaw\workspace\daily_summary.py
```

### 预期输出

```
📝 正在生成 2026-03-17 的每日总结...
   找到 XX 条会话记录
✅ 每日总结已保存到：C:\Users\21326\.openclaw\workspace\memory\daily-summary-2026-03-17.md
```

### 检查输出文件

```bash
# 查看生成的文件
type C:\Users\21326\.openclaw\workspace\memory\daily-summary-2026-03-17.md
```

---

## 📊 生成的总结内容

每日总结文件包含以下部分：

1. **今日概览** - 日期、时间、会话数量
2. **主要成就** - 今天完成的重要任务
3. **创建的文件** - 今天新建的文件列表
4. **待办事项** - 未完成的任务
5. **今日学习** - 核心知识点和踩坑记录
6. **明日计划** - 明天的工作计划

---

## ⚠️ 注意事项

### 1. Python 环境
确保 Python 已安装并添加到 PATH：

```bash
python --version
```

如果没有安装，需要：
1. 下载安装 Python 3.8+
2. 勾选 "Add Python to PATH"
3. 重启终端

### 2. 权限问题
如果任务执行失败，尝试：
- 以管理员身份运行任务计划程序
- 在任务属性中勾选"使用最高权限运行"

### 3. 日志查看
如果任务执行失败，查看：
- 任务计划程序 → 任务 → 历史记录
- 或者手动执行脚本查看错误信息

### 4. 会话记录访问
脚本需要读取会话日志，确保：
- OpenClaw 会话日志路径正确
- 有权限访问该目录

---

## 🔧 自定义配置

### 修改总结时间

编辑定时任务，将时间从 `22:00` 改为其他时间。

### 修改输出目录

编辑 `daily_summary.py`，修改：

```python
WORKSPACE_DIR = Path(r"你的工作区路径")
MEMORY_DIR = WORKSPACE_DIR / "memory"
```

### 修改总结模板

编辑 `daily_summary.py` 中的 `generate_daily_summary()` 函数，自定义总结内容格式。

---

## 📝 示例输出

查看今天的总结示例：

```bash
type C:\Users\21326\.openclaw\workspace\memory\daily-summary-2026-03-17.md
```

---

## 🔗 相关文档

- [每日总结示例](./memory/daily-summary-2026-03-17.md)
- [总结生成脚本](./daily_summary.py)
- [DolphinScheduler 完整指南](./DOLPHINSCHEDULER_COMPLETE_GUIDE.md)

---

**最后更新：** 2026-03-17 17:48 GMT+8
