# 配置备份说明

## 备份时间
2026-03-24

## 备份内容
- openclaw.json: OpenClaw 完整配置文件

## 关键配置

### Webhook 配置（已修复但可能不生效）
- enabled: true
- token: wattrel-webhook-secret-token-2026
- path: /hooks/wattrel
- sessionKey: 已更新为正确的钉钉群会话

### 推荐方案
使用 `sessions_send` 方式发送告警（已验证可靠）

## 已知问题
- Webhook 返回 200 但消息未送达（session 匹配问题）
- sessions_send 方式已验证可用

## 相关脚本
- alert/alert_query_final.py: 使用 sessions_send 的最终版本
