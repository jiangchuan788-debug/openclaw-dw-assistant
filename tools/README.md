# tools/ 目录

**用途**: 工具脚本

## 文件说明

| 文件 | 用途 |
|------|------|
| `extract_ds_sql.py` | 提取 DolphinScheduler 项目中的 SQL 代码 |
| `task_execution_checker.py` | 检查定时任务执行环境 |

## 使用方法

### 提取 SQL
```bash
# 提取指定项目的 SQL
python3 tools/extract_ds_sql.py <project_code> --name <project_name>

# 示例
python3 tools/extract_ds_sql.py 159737550740160 --name okr_ads
```

### 检查任务环境
```bash
# 检查所有任务
python3 tools/task_execution_checker.py --task all

# 检查指定任务
python3 tools/task_execution_checker.py --task abnormal
python3 tools/task_execution_checker.py --task repair
```
