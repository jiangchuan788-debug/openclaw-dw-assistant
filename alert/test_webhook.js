const mysql = require('/tmp/node_modules/mysql2/promise');
const http = require('http');

// 数据库配置
const DB_CONFIG = {
    host: '172.20.0.235',
    port: 13306,
    user: 'e_ds',
    password: 'hAN0Hax1lop',
    database: 'wattrel',
    charset: 'utf8mb4'
};

// OpenClaw Webhook 配置
const OPENCLAW_WEBHOOK = 'http://127.0.0.1:18789/hooks/wattrel/wake';
const OPENCLAW_HOOK_TOKEN = 'wattrel-webhook-secret-token-2026';

// 发送给 OpenClaw
function sendToOpenClaw(message) {
    return new Promise((resolve, reject) => {
        const url = new URL(OPENCLAW_WEBHOOK);
        
        const options = {
            hostname: url.hostname,
            port: url.port,
            path: url.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${OPENCLAW_HOOK_TOKEN}`
            }
        };
        
        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                if (res.statusCode === 200 || res.statusCode === 202) {
                    resolve({ success: true, status: res.statusCode });
                } else {
                    resolve({ success: false, status: res.statusCode, data });
                }
            });
        });
        
        req.on('error', (err) => {
            resolve({ success: false, error: err.message });
        });
        
        req.write(JSON.stringify({ text: message, mode: 'now' }));
        req.end();
    });
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
    console.log('🚀 OpenClaw 告警桥接 - Webhook 测试模式');
    console.log('='.repeat(70));
    console.log(`📡 Webhook: ${OPENCLAW_WEBHOOK}`);
    console.log(`💾 数据库: ${DB_CONFIG.host}:${DB_CONFIG.port}/${DB_CONFIG.database}`);
    console.log();

    let connection;
    const processedIds = [];
    
    try {
        // 连接数据库
        connection = await mysql.createConnection(DB_CONFIG);
        console.log('✅ 数据库连接成功\n');
        
        // 只查询1条告警进行测试
        const [alerts] = await connection.execute(`
            SELECT id, content, type, status, created_at
            FROM wattrel_quality_alert
            WHERE status = 0
            ORDER BY created_at DESC
            LIMIT 1
        `);
        
        if (alerts.length === 0) {
            console.log('✅ 没有未处理的告警');
            return;
        }
        
        const alert = alerts[0];
        
        // 格式化告警消息
        let content = alert.content || '';
        let mainContent = content;
        let sqlContent = '';
        
        if (content.includes('【执行语句】')) {
            const parts = content.split('【执行语句】');
            mainContent = parts[0].trim();
            sqlContent = parts[1].trim();
        }
        
        const formattedMsg = `🚨 数据质量告警 #${alert.id}
【级别】P${alert.type || '1'}
【时间】${alert.created_at}
【内容】${mainContent}
${sqlContent ? '【SQL】' + sqlContent.substring(0, 200) + '...' : ''}`;
        
        console.log('📋 准备发送告警到钉钉群...');
        console.log('-'.repeat(70));
        console.log(formattedMsg);
        console.log('-'.repeat(70));
        
        // 发送给 OpenClaw
        const result = await sendToOpenClaw(formattedMsg);
        
        if (result.success) {
            console.log(`✅ 发送成功 (HTTP ${result.status})`);
            processedIds.push(alert.id);
            
            // 更新状态
            await updateAlertStatus(connection, processedIds);
            console.log(`💾 已标记告警 ${alert.id} 为处理完成`);
            
            console.log('\n🎉 测试成功！我应该能在钉钉群收到这条告警！');
        } else {
            console.log(`❌ 发送失败: ${result.error || `HTTP ${result.status}`}`);
        }
        
    } catch (err) {
        console.error(`\n❌ 错误: ${err.message}`);
    } finally {
        if (connection) {
            await connection.end();
            console.log('📌 数据库连接已关闭');
        }
    }
}

main();
