#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
显示所有已处理的新闻链接
"""

import json
import datetime

def show_all_processed_news():
    """显示所有已处理的新闻链接"""
    
    # 获取当前时间
    now = datetime.datetime.now()
    today = now.date()
    today_str = today.strftime('%Y-%m-%d')
    
    print(f"📰 所有已处理的新闻链接")
    print("=" * 60)
    print(f"📅 日期: {today_str}")
    print(f"🕐 当前时间: {now.strftime('%H:%M')}")
    print()
    
    # 读取历史记录
    history_file = "history.json"
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        
        if 'processed_urls' in history_data:
            processed_urls = history_data['processed_urls']
            
            print(f"📊 今日已处理新闻: {len(processed_urls)} 条")
            print()
            
            # 显示所有新闻链接
            for i, url in enumerate(processed_urls, 1):
                print(f"{i:3d}. {url}")
            
            print()
            print(f"✅ 总计: {len(processed_urls)} 条新闻已处理")
            
        else:
            print("⚠️  历史记录中没有找到已处理的URL列表")
    
    except FileNotFoundError:
        print(f"⚠️  未找到历史记录文件: {history_file}")
        print("💡 提示: 系统可能尚未运行过新闻抓取程序")
    except json.JSONDecodeError:
        print(f"⚠️  历史记录文件格式错误: {history_file}")
    except Exception as e:
        print(f"⚠️  读取历史记录时出错: {e}")

if __name__ == "__main__":
    show_all_processed_news()