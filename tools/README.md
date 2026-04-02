# tools/ 目录

**用途**: 工具脚本

## 文件说明

| 文件 | 用途 |
|------|------|
| `extract_ds_sql.py` | 提取 DolphinScheduler 项目中的内嵌 SQL |
| `extract_ds_sh_usage.py` | 提取 DS 项目里 `.sh` 资源/脚本使用清单 |
| `fill_ds_workflow_resources.py` | 给指定工作流任务补 `resourceList` |
| `update_ds_dwd_shell_script.py` | 批量更新 DWD 任务脚本和环境 |
| `task_execution_checker.py` | 检查定时任务执行环境 |

## 使用方法

### 提取 SQL
```bash
# 提取指定项目的 SQL
python3 tools/extract_ds_sql.py --project-name <project_name> --output ./sql_export/<project_name>

# 示例
python3 tools/extract_ds_sql.py --project-name DW_DM --output ./sql_export/DW_DM
```

### 提取 .sh 使用清单
```bash
python3 tools/extract_ds_sh_usage.py DW_DM DW_DWD DW_RPT --output ./sql_export/all_projects_sh_usage.csv
```

### 回填任务资源文件
```bash
# 预览
python3 tools/fill_ds_workflow_resources.py --project-name '巴基斯坦-数仓工作流_new' --workflow-name 'DWD'

# 提交
python3 tools/fill_ds_workflow_resources.py --project-name '巴基斯坦-数仓工作流_new' --workflow-name 'DWD' --apply
```

### 批量更新 DWD 任务脚本和环境
```bash
# 预览
python3 tools/update_ds_dwd_shell_script.py --project-name '巴基斯坦-数仓工作流_new' --workflow-name 'DWD'

# 提交
python3 tools/update_ds_dwd_shell_script.py --project-name '巴基斯坦-数仓工作流_new' --workflow-name 'DWD' --apply
```

### 检查任务环境
```bash
# 检查所有任务
python3 tools/task_execution_checker.py --task all

# 检查指定任务
python3 tools/task_execution_checker.py --task abnormal
python3 tools/task_execution_checker.py --task repair
```

## 依赖环境

```bash
export DS_BASE_URL='http://127.0.0.1:12345/dolphinscheduler'
export DS_TOKEN='your_token'
```

说明：
- 上面 4 个 DS API 脚本已经按当前本地隧道地址适配。
- 默认建议先 dry-run，再带 `--apply` 执行真实更新。
