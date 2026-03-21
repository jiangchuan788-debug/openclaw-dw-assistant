# OpenClaw 告警自动化系统 - 完整配置指南

> **日期：** 2026-03-19  
> **作者：** 陈江川 + OpenClaw 数据平台  
> **目的：** 让其他 OpenClaw 实例可以复现这套告警自动化流程

---

## 📐 系统架构

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  数据库告警表    │ ──→ │  alert_bridge.py  │ ──→ │  OpenClaw Hook   │
│ wattrel_quality │     │  (告警搬运工)     │     │  /hooks/wattrel  │
│ _alert          │     │                  │     │                  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                        │
         │                       │                        │
         ▼                       ▼                        ▼
   status=0 未处理          扫描新告警              格式化发送
   status=1 已处理          格式化消息              到钉钉群
```

---

## 🔧 核心组件

### 1️⃣ 数据库配置

```python
# alert_bridge.py 配置区
DB_HOST = '127.0.0.1'      # 本地 SSH 隧道端口
DB_PORT = 3333              # 隧道映射端口
DB_USER = 'e_ds'            # 数据库账号
DB_PASS = 'hAN0Hax1lop'     # 数据库密码
DB_NAME = 'wattrel'         # 数据库名
```

**SSH 隧道命令（如需远程连接）：**
```bash
ssh -L 3333:远程 DB 地址:3306 用户@跳板机
```

---

### 2️⃣ OpenClaw Hook 配置

**关键点：** Hook 端点路径需要在 OpenClaw 配置中正确设置

```yaml
# OpenClaw 配置文件中的 hooks 配置
hooks:
  path: "/hooks"  # ✅ 确保这个路径正确
  wattrel:
    token: "MySecretAlertToken123"
```

**Webhook 地址：**
```
http://127.0.0.1:18789/hooks/wattrel/wake
```

**请求格式：**
```json
{
  "text": "告警消息内容",
  "mode": "now"
}
```

**认证 Header：**
```
Authorization: Bearer MySecretAlertToken123
Content-Type: application/json
```

**常见错误：**
| 错误码 | 原因 | 解决方案 |
|--------|------|----------|
| 404 | `hooks.path` 配置错误 | 检查 OpenClaw 配置中 `hooks.path` 是否为 `/hooks` |
| 401 | Token 不匹配 | 确保 Header 中 Token 正确 |
| 200/202 | 成功 | 配置正确 |

---

### 3️⃣ 告警消息格式

**输入（数据库 content 字段）：**
```
指标校验异常 ods_qsq_erp_atransaction 数量不一致 期望值 202776 实际值 202778 差值为 -2
【执行语句】SELECT COUNT(*) as cnt FROM biz_qsq_catalog.qsq_erp.atransaction WHERE...
```

**输出（发送到钉钉群）：**
```
【任务名称】数据质量校验任务_12345
【告警时间】2026-03-18 17:50:42
【告警级别】P3
【校验时间】03 月 17 日 00 时 至 03 月 18 日 00 时
【告警内容】指标校验异常 ods_qsq_erp_atransaction 数量不一致 期望值 202776 实际值 202778 差值为 -2
【执行语句】SELECT COUNT(*) as cnt FROM biz_qsq_catalog.qsq_erp.atransaction WHERE...
```

**字段说明：**
| 字段 | 来源 | 说明 |
|------|------|------|
| 任务名称 | 自动生成 | `数据质量校验任务_{alert_id}` |
| 告警时间 | `created_at` | 告警创建时间 |
| 告警级别 | `type` | P1/P2/P3（type 字段转换） |
| 校验时间 | 从 content 提取 | 数据校验的时间范围 |
| 告警内容 | `content` | 【执行语句】之前的部分 |
| 执行语句 | `content` | 【执行语句】之后的 SQL |

---

### 4️⃣ 核心代码逻辑

```python
# 1. 抓取未处理告警
cursor.execute("""
    SELECT id, content, created_at 
    FROM wattrel_quality_alert 
    WHERE status = 0 
    ORDER BY created_at ASC
    LIMIT 2
""")

# 2. 格式化消息
if "【执行语句】" in content:
    parts = content.split("【执行语句】", 1)
    main_content = parts[0].strip()
    sql_content = parts[1].strip()

formatted_msg = f"""【任务名称】数据质量校验任务_{alert['id']}
【告警时间】{alert['created_at']}
【告警级别】P{alert.get('type', 1)}
【告警内容】{main_content}
【执行语句】{sql_content}"""

# 3. 发送给 OpenClaw
payload = {"text": formatted_msg, "mode": "now"}
response = requests.post(
    OPENCLAW_WEBHOOK, 
    json=payload, 
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENCLAW_HOOK_TOKEN}"
    }
)

# 4. 回写数据库状态
cursor.execute(f"UPDATE wattrel_quality_alert SET status = 1 WHERE id IN ({ids_str})")
```

---

### 5️⃣ 定时任务配置

**方式 A：Windows 任务计划程序（推荐）**

创建每小时执行的任务：
```powershell
schtasks /Create /TN "OpenClaw Alert Bridge" /TR "D:\anconda3\python.exe C:\Users\21326\.openclaw\workspace\alert_bridge.py --once" /SC HOURLY /RL HIGHEST /F
```

验证任务：
```powershell
schtasks /Query /TN "OpenClaw Alert Bridge"
```

**方式 B：Python 守护进程**
```bash
# 每 30 分钟轮询一次
python alert_bridge.py --interval 30
```

**方式 C：手动触发**
```bash
# 只运行一次扫描
python alert_bridge.py --once
```

---

## 🧪 测试流程

### Step 1: 测试数据库连接
```python
python -c "
import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3333, user='e_ds', password='hAN0Hax1lop', database='wattrel')
print('✅ 数据库连接成功')
conn.close()
"
```

### Step 2: 测试 Webhook 端点
```bash
curl -X POST http://127.0.0.1:18789/hooks/wattrel/wake ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer MySecretAlertToken123" ^
  -d "{\"text\":\"测试消息\",\"mode\":\"now\"}"
```

### Step 3: 手动触发告警扫描
```bash
python alert_bridge.py --once
```

**预期输出：**
```
============================================================
🚀 OpenClaw 告警雷达 - 手动触发模式
============================================================
📡 Webhook 地址：http://127.0.0.1:18789/hooks/wattrel/wake
💾 数据库：127.0.0.1:3333/wattrel
------------------------------------------------------------

[11:15:30] 🚨 发现 2 条新告警，准备投递给 AI 大脑...
 ✅ 告警 [ID: 12345] 投递成功！
 ✅ 告警 [ID: 12346] 投递成功！
[11:15:31] 数据库回写完毕，已标记为处理完成 (status=1)。

✅ 扫描完成，程序退出。
```

---

## ⚠️ 踩坑记录

| 问题 | 现象 | 解决方案 |
|------|------|----------|
| Hook 404 | `/hooks/wattrel/wake` 返回 404 | 检查 OpenClaw 配置中 `hooks.path` 是否为 `/hooks` |
| Token 认证失败 | 401 Unauthorized | 确保 Header 中 `Authorization: Bearer <token>` 格式正确 |
| 数据库连接超时 | Connection refused | 确认 SSH 隧道已建立，端口 3333 可访问 |
| 重复告警 | 同一条告警多次发送 | 确保扫描后更新 `status=1` |
| 中文乱码 | 告警内容显示乱码 | 数据库连接添加 `charset='utf8mb4'`，Python 脚本添加 UTF-8 输出编码 |

---

## 📁 文件清单

| 文件 | 说明 | 路径 |
|------|------|------|
| `alert_bridge.py` | 告警搬运工主脚本 | workspace 根目录 |
| `alert_bridge_hourly.ps1` | 每小时定时任务脚本 | workspace 根目录 |
| `ALERT_AUTOMATION_GUIDE.md` | 完整配置指南 | workspace 根目录 |
| `memory/2026-03-18.md` | 搭建日志 | memory/目录 |

---

## 🔐 安全建议

1. **Token 管理** - 不要将 `OPENCLAW_HOOK_TOKEN` 提交到代码仓库
2. **数据库权限** - 使用只读账号扫描告警，写操作限制在 status 字段
3. **SSH 隧道** - 远程数据库必须通过隧道访问，不要直接暴露
4. **日志脱敏** - 生产环境日志中隐藏密码和敏感信息

---

## 🚀 快速复现步骤

```bash
# 1. 克隆脚本
git clone <你的仓库> alert-bridge
cd alert-bridge

# 2. 安装依赖
pip install pymysql requests

# 3. 配置参数
# 编辑 alert_bridge.py，修改数据库配置和 Webhook 地址

# 4. 测试连接
python alert_bridge.py --once

# 5. 配置定时任务
# Windows: 任务计划程序 → 创建任务 → 每小时执行 alert_bridge_hourly.ps1
# Linux: crontab -e → 0 * * * * /path/to/alert_bridge_hourly.sh
```

---

## 📊 系统意义

### 解决的问题
1. **人工监控效率低** - 传统方式需要人工查看数据库告警表
2. **响应延迟** - 发现告警到处理有时间差
3. **信息分散** - 告警内容、SQL、时间等信息分散在不同字段

### 带来的价值
1. **实时响应** - 告警产生后自动触发 AI 处理
2. **格式统一** - 标准化告警消息格式，便于阅读和处理
3. **闭环管理** - 自动回写状态，防止重复告警
4. **可扩展** - 其他系统可复用此架构

### 适用场景
- 数据库质量监控告警
- 业务指标异常告警
- 系统健康度监控
- 任何需要 AI 自动处理的数据库告警场景

---

**最后更新：** 2026-03-19 11:25 GMT+8  
**维护者：** 陈江川 + OpenClaw 数据平台
