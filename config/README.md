# config/ 目录

**用途**: 系统配置文件

## 文件说明

| 文件 | 用途 |
|------|------|
| `config.py` | 配置管理，安全读取Token等敏感信息 |
| `auto_load_env.py` | 自动从 ~/.bashrc 加载环境变量 |

## 环境变量要求

使用前确保已设置以下环境变量（在 ~/.bashrc 中）:

```bash
export DS_TOKEN='your_ds_token'
export DB_PASSWORD='your_db_password'
export DB_HOST='172.20.0.235'
export DB_PORT='13306'
export DB_USER='e_ds'
export DB_NAME='wattrel'
```
