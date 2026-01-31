#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取今日新闻摘要的简单脚本
"""
import json
import os
from datetime import datetime
import sys

def get_recent_news():
    """获取最近的新闻记录"""
    try:
        # 读取历史记录文件
        if os.path.exists('history.json'):
            with open('history.json', 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                
            print("📰 每日AI新闻摘要")
            print("="*50)
            print(f"📅 日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📊 总计已处理新闻链接: {len(history_data.get('processed_urls', []))}")
            
            # 显示最近处理的一些新闻链接
            recent_urls = history_data.get('processed_urls', [])[-10:]  # 最近10个
            
            print("\n📋 最近处理的新闻链接:")
            for i, url in enumerate(recent_urls, 1):
                print(f"{i}. {url}")
                
            print("\n💡 提示: 由于当前环境限制，实际的AI分析和飞书推送可能未完成")
            print("   但系统已成功获取并准备处理这些新闻源。")
            
        else:
            print("⚠️ 历史记录文件不存在，可能是首次运行")
            
    except Exception as e:
        print(f"❌ 获取新闻时出错: {str(e)}")

if __name__ == "__main__":
    get_recent_news()