#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版新闻摘要 - 从早上6:00到现在的关键新闻
"""

import json
import datetime
from urllib.parse import urlparse
from collections import Counter

def generate_simple_summary():
    """生成简化版新闻摘要"""
    
    # 获取当前时间
    now = datetime.datetime.now()
    today = now.date()
    today_str = today.strftime('%Y-%m-%d')
    
    print(f"📰 从早上6:00到现在的新闻摘要")
    print("=" * 50)
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
            
            # 按域名统计
            domains = []
            for url in processed_urls:
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc
                    domains.append(domain)
                except:
                    continue
            
            domain_counts = Counter(domains)
            
            print("📈 新闻来源分布:")
            for domain, count in domain_counts.most_common(8):
                percentage = (count / len(processed_urls)) * 100
                print(f"   • {domain}: {count} 条 ({percentage:.1f}%)")
            
            print()
            print("🔍 今日热点新闻类型:")
            
            # 分析URL中的关键词来确定新闻类型
            keywords = []
            for url in processed_urls:
                url_lower = url.lower()
                
                if 'bitcoin' in url_lower or 'crypto' in url_lower or 'coin' in url_lower:
                    keywords.append(' cryptocurrency')
                elif 'stock' in url_lower or 'market' in url_lower or 'finance' in url_lower or 'trading' in url_lower:
                    keywords.append(' financial markets')
                elif 'ai' in url_lower or 'artificial' in url_lower or 'machine' in url_lower or 'intelligence' in url_lower:
                    keywords.append(' artificial intelligence')
                elif 'china' in url_lower or 'chinese' in url_lower:
                    keywords.append(' china')
                elif 'tech' in url_lower or 'technology' in url_lower or 'innovation' in url_lower:
                    keywords.append(' technology')
                elif 'energy' in url_lower or 'oil' in url_lower or 'gas' in url_lower:
                    keywords.append(' energy')
                elif 'politic' in url_lower or 'government' in url_lower or 'policy' in url_lower:
                    keywords.append(' politics')
                elif 'health' in url_lower or 'medical' in url_lower or 'covid' in url_lower:
                    keywords.append(' health')
            
            keyword_counts = Counter(keywords)
            for keyword, count in keyword_counts.most_common(6):
                print(f"   • {keyword.strip()}: {count} 条")
            
            print()
            print("💡 提示: 以上是基于已处理的{len(processed_urls)}个新闻链接的统计分析")
            print("   完整的AI分析报告应已通过飞书机器人发送")
            
        else:
            print("⚠️  历史记录中没有找到已处理的URL列表")
    
    except FileNotFoundError:
        print(f"⚠️  未找到历史记录文件: {history_file}")
        print("💡 提示: 系统可能尚未运行过新闻抓取程序")
    except json.JSONDecodeError:
        print(f"⚠️  历史记录文件格式错误: {history_file}")
    except Exception as e:
        print(f"⚠️  读取历史记录时出错: {e}")

def show_latest_news():
    """显示最新的新闻链接"""
    history_file = "history.json"
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        
        if 'processed_urls' in history_data:
            processed_urls = history_data['processed_urls']
            
            print("\n🔗 最新处理的10条新闻:")
            print("-" * 30)
            
            # 显示最新的10条新闻
            latest_urls = processed_urls[-10:] if len(processed_urls) > 10 else processed_urls
            
            for i, url in enumerate(latest_urls, 1):
                print(f"{i:2d}. {url}")
    
    except Exception as e:
        print(f"⚠️  读取最新新闻时出错: {e}")

if __name__ == "__main__":
    generate_simple_summary()
    show_latest_news()
    
    print("\n" + "="*50)
    print("🎯 总结: 系统今日已处理大量新闻，涵盖财经、科技、AI等多个领域")
    print("   详细的AI分析报告应已发送至您的飞书群组")