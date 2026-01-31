#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速显示今天已处理的新闻链接
"""

import json
import datetime
from urllib.parse import urlparse
from collections import defaultdict

def show_processed_news():
    """显示已处理的新闻链接"""
    
    # 获取今天的日期
    today = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')
    
    print(f"📰 今日已处理的新闻链接概览")
    print("=" * 60)
    print(f"📅 日期: {today_str}")
    print()
    
    # 读取历史记录
    history_file = "history.json"
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        
        if 'processed_urls' in history_data:
            processed_urls = history_data['processed_urls']
            
            print(f"📊 总计已处理新闻链接: {len(processed_urls)}")
            print()
            
            # 按域名分组URL
            domain_groups = defaultdict(list)
            for url in processed_urls:
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc
                    domain_groups[domain].append(url)
                except:
                    continue
            
            # 显示每个域名的链接数量
            print("📈 按来源分类:")
            for domain, urls in sorted(domain_groups.items(), key=lambda x: len(x[1]), reverse=True):
                print(f"   • {domain}: {len(urls)} 条")
            
            print()
            print("🔗 最近处理的30个链接:")
            print("-" * 50)
            
            # 显示最近的链接
            recent_urls = processed_urls[-30:] if len(processed_urls) > 30 else processed_urls
            
            for i, url in enumerate(recent_urls, 1):
                print(f"{i:2d}. {url}")
            
            print()
            print("💡 提示: 这些是系统今天已处理的新闻链接，按处理顺序排列")
            print("   由于历史记录中没有时间戳，无法精确确定每个链接的处理时间")
            
        else:
            print("⚠️  历史记录中没有找到已处理的URL列表")
    
    except FileNotFoundError:
        print(f"⚠️  未找到历史记录文件: {history_file}")
        print("💡 提示: 系统可能尚未运行过新闻抓取程序")
    except json.JSONDecodeError:
        print(f"⚠️  历史记录文件格式错误: {history_file}")
    except Exception as e:
        print(f"⚠️  读取历史记录时出错: {e}")

def show_sample_news_analysis():
    """显示一些示例新闻分析格式"""
    print("\n📋 示例新闻分析格式:")
    print("-" * 30)
    print("标题: [新闻标题]")
    print("来源: [新闻网站]")
    print("时间: [发布日期]")
    print("摘要: [AI生成的摘要]")
    print("情绪: [正面/负面/中性]")
    print("重要度: [1-10分]")
    print("标签: [关键词标签]")

if __name__ == "__main__":
    show_processed_news()
    show_sample_news_analysis()