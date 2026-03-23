const mysql = require('/tmp/node_modules/mysql2/promise');
const fs = require('fs');
const path = require('path');

// 配置
const DB_CONFIG = {
    host: '172.20.0.235',
    port: 13306,
    user: 'e_ds',
    password: 'hAN0Hax1lop',
    database: 'wattrel',
    charset: 'utf8mb4'
};

// 告警输出目录
const ALERT_OUTPUT_DIR = '/home/node/.openclaw/workspace/alert/output';

// 格式化告警消息
function formatAlert(alert) {
    let content = alert.content || '';
    let mainContent = content;
    let sqlContent = '';
    
    if (content.includes('【执行语句】')) {
        const parts = content.split('【执行语句】');
        mainContent = parts[0].trim();
        sqlContent = parts[1].trim();
    }
    
    const formattedMsg = `【任务名称】数据质量校验任务_${alert.id}
【告警时间】${alert.created_at}
【告警级别】P${alert.type || '1'}
【告警内容】${mainContent}
${sqlContent ? '【执行语句】' + sqlContent : ''}`;
    
    return formattedMsg;
}

// 保存告警到文件
function saveAlertToFile(alert, formattedMsg) {
    if (!fs.existsSync(ALERT_OUTPUT_DIR)) {
        fs.mkdirSync(ALERT_OUTPUT_DIR, { recursive: true });
    }
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `alert_${alert.id}_${timestamp}.txt`;
    const filepath = path.join(ALERT_OUTPUT_DIR, filename);
    
    fs.writeFileSync(filepath, formattedMsg, 'utf8');
    return filepath;
}

// 更新告警状态
async function updateAlertStatus(connection, ids) {
    if (ids.length === 0) return;
    const placeholders = ids.map(() => '?').join(',');
    await connection.execute(
        `UPDATE wattrel_quality_alert SET status = 1 WHERE id IN (${placeholders})`,
        ids
    );
}

// 主函数
async function main() {
    console.log('='.repeat(70));
    console.log('🚀 OpenClaw 告警桥接 (Node.js) - 本地模式');
    console.log('='.repeat(70));
    console.log(`💾 数据库: ${DB_CONFIG.host}:${DB_CONFIG.port}/${DB_CONFIG.database}`);
    console.log(`📁 输出目录: ${ALERT_OUTPUT_DIR}`);
    console.log();

    let connection;
    const processedIds = [];
    
    try {
        // 连接数据库
        connection = await mysql.createConnection(DB_CONFIG);
        console.log('✅ 数据库连接成功\n');
        
        // 查询未处理告警（取前10条）
        const [alerts] = await connection.execute(`
            SELECT id, content, type, status, created_at
            FROM wattrel_quality_alert
            WHERE status = 0
            ORDER BY created_at DESC
            LIMIT 10
        `);
        
        if (alerts.length === 0) {
            console.log('✅ 没有未处理的告警');
            return;
        }
        
        console.log(`🚨 发现 ${alerts.length} 条新告警\n`);
        console.log('='.repeat(70));
        
        // 逐条处理
        for (let i = 0; i < alerts.length; i++) {
            const alert = alerts[i];
            const formattedMsg = formatAlert(alert);
            
            console.log(`\n[${i + 1}/${alerts.length}] 📋 告警 ID: ${alert.id}`);
            console.log('-'.repeat(70));
            console.log(formattedMsg);
            console.log('-'.repeat(70));
            
            // 保存到文件
            const filepath = saveAlertToFile(alert, formattedMsg);
            console.log(`💾 已保存到: ${filepath}`);
            
            processedIds.push(alert.id);
            
            // 间隔 0.5 秒
            if (i < alerts.length - 1) {
                await new Promise(r => setTimeout(r, 500));
            }
        }
        
        // 更新已处理的告警状态
        if (processedIds.length > 0) {
            await updateAlertStatus(connection, processedIds);
            console.log(`\n${'='.repeat(70)}`);
            console.log(`✅ 已处理 ${processedIds.length} 条告警`);
            console.log(`💾 已标记为处理完成 (status=1)`);
            console.log(`📁 告警文件保存在: ${ALERT_OUTPUT_DIR}`);
        }
        
        console.log('\n✅ 告警处理完成！');
        
    } catch (err) {
        console.error(`\n❌ 错误: ${err.message}`);
        console.error(err.stack);
    } finally {
        if (connection) {
            await connection.end();
            console.log('📌 数据库连接已关闭');
        }
    }
}

main();
