#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
告警数据库测试脚本
查询 wattrel_quality_alert 表中未处理的告警

作者: OpenClaw
日期: 2026-03-23
"""

import pymysql
import json

# 数据库配置
DB_CONFIG = {
    'host': '172.20.0.235',
    'port': 13306,
    'user': 'e_ds',
    'password': 'hAN0Hax1lop',
    'database': 'wattrel',
    'charset': 'utf8mb4'
}

def test_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("🔍 告警数据库连接测试")
    print("=" * 60)
    print(f"📍 地址: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"👤 用户: {DB_CONFIG['user']}")
    print(f"📊 数据库: {DB_CONFIG['database']}")
    print()
    
    try:
        conn = pymysql.connect(**DB_CONFIG)
        print("✅ 数据库连接成功！")
        return conn
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return None

def query_unprocessed_alerts(conn):
    """查询未处理告警 (status=0)"""
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # 查询未处理告警
    cursor.execute("""
        SELECT id, content, type, status, created_at, updated_at
        FROM wattrel_quality_alert
        WHERE status = 0
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    alerts = cursor.fetchall()
    
    print("\n" + "=" * 60)
    print(f"🚨 未处理告警列表 (共 {len(alerts)} 条)")
    print("=" * 60)
    
    if not alerts:
        print("✅ 当前没有未处理的告警")
        return
    
    for alert in alerts:
        print(f"\n📋 告警 ID: {alert['id']}")
        print(f"   级别: P{alert.get('type', 'N/A')}")
        print(f"   状态: {'未处理' if alert['status'] == 0 else '已处理'}")
        print(f"   创建时间: {alert['created_at']}")
        
        # 格式化内容
        content = alert.get('content', '')
        if '【执行语句】' in content:
            parts = content.split('【执行语句】', 1)
            main_content = parts[0].strip()
            sql = parts[1].strip()[:100] + '...' if len(parts[1]) > 100 else parts[1].strip()
            print(f"   内容: {main_content[:80]}...")
            print(f"   SQL: {sql}")
        else:
            print(f"   内容: {content[:100]}...")
        print("-" * 60)
    
    cursor.close()

def query_alert_stats(conn):
    """查询告警统计"""
    cursor = conn.cursor()
    
    # 统计总数
    cursor.execute("SELECT COUNT(*) FROM wattrel_quality_alert")
    total = cursor.fetchone()[0]
    
    # 统计未处理
    cursor.execute("SELECT COUNT(*) FROM wattrel_quality_alert WHERE status = 0")
    unprocessed = cursor.fetchone()[0]
    
    # 统计已处理
    cursor.execute("SELECT COUNT(*) FROM wattrel_quality_alert WHERE status = 1")
    processed = cursor.fetchone()[0]
    
    print("\n" + "=" * 60)
    print("📊 告警统计")
    print("=" * 60)
    print(f"   总计: {total} 条")
    print(f"   🚨 未处理: {unprocessed} 条")
    print(f"   ✅ 已处理: {processed} 条")
    
    cursor.close()

def main():
    print("\n🚀 启动告警数据库测试...\n")
    
    # 测试连接
    conn = test_connection()
    if not conn:
        print("\n❌ 测试失败，请检查:")
        print("   1. 数据库地址和端口是否正确")
        print("   2. 用户名密码是否正确")
        print("   3. 网络是否可达")
        return
    
    try:
        # 查询统计
        query_alert_stats(conn)
        
        # 查询未处理告警
        query_unprocessed_alerts(conn)
        
        print("\n✅ 测试完成！")
        
    except Exception as e:
        print(f"\n❌ 查询失败: {e}")
    finally:
        conn.close()
        print("\n📌 连接已关闭")

if __name__ == '__main__':
    main()
