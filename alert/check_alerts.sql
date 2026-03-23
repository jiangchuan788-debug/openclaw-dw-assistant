-- 告警数据库查询
-- 在 MySQL 客户端中执行

-- 1. 查看数据库列表
SHOW DATABASES;

-- 2. 切换到 wattrel 库
USE wattrel;

-- 3. 查看告警表结构
DESCRIBE wattrel_quality_alert;

-- 4. 查询未处理告警统计
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) as unprocessed,
    SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) as processed
FROM wattrel_quality_alert;

-- 5. 查询最近10条未处理告警
SELECT 
    id,
    content,
    type,
    status,
    created_at
FROM wattrel_quality_alert
WHERE status = 0
ORDER BY created_at DESC
LIMIT 10;

-- 6. 按类型统计告警
SELECT 
    type,
    COUNT(*) as count,
    SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) as unprocessed
FROM wattrel_quality_alert
GROUP BY type;
