# OpenClaw 配置备份

**备份时间：** 2026-03-23  
**配置文件：** `~/.openclaw/openclaw.json`

---

## 关键配置信息

### Gateway 配置
| 项目 | 值 |
|------|-----|
| Port | `18789` |
| Mode | `local` |
| Bind | `lan` |
| Token | `86fd5a864e986b4ed4244fd7ef746f177fa8090a2e30b404` |

### DingTalk 配置
| 项目 | 值 |
|------|-----|
| Client ID | `dingqod71dmvfgl0wyq1` |
| Corp ID | `ding49dceee635ecfd274ac5d6980864d335` |
| Agent ID | `4363310564` |

### 模型配置
| 模型 | 别名 |
|------|------|
| `kimi-coding/k2p5` | Kimi for Coding |
| `moonshot/kimi-k2.5` | Kimi |
| `google/gemini-3.1-pro-preview` | - |

### Hooks 配置
当前只有内部 hooks，**缺少 `wattrel` webhook**：
- `boot-md`
- `bootstrap-extra-files`
- `command-logger`
- `session-memory`

---

## 需要添加的配置

如需支持告警 webhook，需添加：

```json
{
  "hooks": {
    "wattrel": {
      "enabled": true,
      "token": "MySecretAlertToken123"
    }
  }
}
```

Webhook 地址：`http://127.0.0.1:18789/hooks/wattrel/wake`

---

**完整配置备份见：** `openclaw-config-backup-20260323.json`
