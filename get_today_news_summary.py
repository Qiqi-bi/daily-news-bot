#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取今天从早上6:00开始的新闻摘要
由于历史记录中没有时间戳，此脚本将从RSS源获取最新的新闻
"""

import feedparser
import json
import datetime
import requests
from urllib.parse import urlparse
import time
import os

# RSS源列表（从fetch_news.py中提取）
RSS_SOURCES = [
    ("https://feeds.bbci.co.uk/news/world/rss.xml", "BBC World News"),
    ("https://rss.cnn.com/rss/edition.rss", "CNN International"),
    ("https://feeds.reuters.com/reuters/topNews", "Reuters Top News"),
    ("https://www.ft.com/rss/world", "Financial Times"),
    ("https://feeds.a.dj.com/rss/RSSWorldNews.xml", "Wall Street Journal"),
    ("https://rss.nytimes.com/services/xml/rss/nyt/InternationalHome.xml", "New York Times"),
    ("https://www.washingtonpost.com/rss/world/index.xml", "Washington Post"),
    ("https://feeds.skynews.com/feeds/rss/world.xml", "Sky News"),
    ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera"),
    ("https://rss.dw.com/xml/rss-en-all", "Deutsche Welle"),
    ("https://www.france24.com/en/rss", "France 24"),
    ("https://www.globaltimes.cn/rss_en/global.xml", "Global Times"),
    ("https://www.scmp.com/rss/9/feed", "South China Morning Post"),
    ("https://rss.app/feeds/8LoPANQoGAbJ3kQR.xml", "TechCrunch"),
    ("https://feeds.arxiv.org/list/cs.AI/recent", "ArXiv AI Papers"),
    ("https://www.coindesk.com/feed/", "CoinDesk"),
    ("https://oilprice.com/rss/main", "OilPrice.com"),
    ("https://www.reddit.com/r/worldnews/.rss", "Reddit World News"),
    ("https://www.reddit.com/r/videos/.rss", "Reddit Popular Videos"),
    ("https://www.hackernews.cc/rss", "Hacker News"),
    ("https://www.ycombinator.com/news/rss", "Y Combinator News"),
    ("https://rss.app/feeds/q1RDOaVg5zmjqboN.xml", "Yahoo Finance"),
    # 国内主流新闻源
    ("http://news.baidu.com/n?cmd=file&format=rss&tn=rss&sub=0", "百度新闻"),
    ("http://rss.people.com.cn/GB/303140/index.xml", "人民网"),
    ("http://www.xinhuanet.com/politics/news_politics.xml", "新华网"),
    ("http://www.chinanews.com/rss/scroll-news.xml", "中国新闻网"),
    ("https://www.thepaper.cn/rss.jsp", "澎湃新闻"),
    ("http://www.ce.cn/cysc/jg/zxbd/rss2.xml", "中国经济网"),
    # 国内科技新闻
    ("https://www.zhihu.com/rss", "知乎日报"),
    ("https://www.36kr.com/feed", "36氪"),
    ("https://news.qq.com/rss/channels/finance/rss.xml", "腾讯财经"),
    ("https://rss.sina.com.cn/news/china/focus15.xml", "新浪新闻"),
]

def get_news_since_morning():
    """获取从今天早上6:00开始的新闻"""
    
    # 获取当前时间和今天早上6:00的时间
    now = datetime.datetime.now()
    today_morning = datetime.datetime.combine(now.date(), datetime.time(6, 0))
    
    print(f"📰 从早上6:00到现在的新闻摘要")
    print("=" * 60)
    print(f"📅 时间范围: {today_morning.strftime('%Y-%m-%d %H:%M')} 到 {now.strftime('%Y-%m-%d %H:%M')}")
    print()
    
    all_articles = []
    
    print("🔄 正在从RSS源获取新闻...")
    
    for rss_url, source_name in RSS_SOURCES[:5]:  # 只获取前5个主要RSS源以节省时间
        try:
            print(f"   📡 获取 {source_name}...")
            
            # 解析RSS源
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries:
                try:
                    # 解析发布时间
                    pub_date = None
                    if hasattr(entry, 'published_parsed'):
                        if entry.published_parsed:
                            pub_date = datetime.datetime(*entry.published_parsed[:6])
                        else:
                            # 如果没有解析的日期，尝试从published字符串解析
                            if hasattr(entry, 'published'):
                                try:
                                    # 尝试几种常见的日期格式
                                    date_str = entry.published
                                    formats = [
                                        '%a, %d %b %Y %H:%M:%S %z',
                                        '%a, %d %b %Y %H:%M:%S',
                                        '%Y-%m-%dT%H:%M:%SZ',
                                        '%Y-%m-%dT%H:%M:%S.%fZ',
                                        '%Y-%m-%d %H:%M:%S'
                                    ]
                                    
                                    for fmt in formats:
                                        try:
                                            pub_date = datetime.datetime.strptime(date_str.split('+')[0].split('-')[0], fmt)
                                            break
                                        except ValueError:
                                            continue
                                except:
                                    pass
                    
                    # 如果无法解析日期，跳过此条目
                    if pub_date is None:
                        continue
                    
                    # 检查是否在时间范围内
                    if today_morning <= pub_date <= now:
                        article = {
                            'title': getattr(entry, 'title', '无标题'),
                            'link': getattr(entry, 'link', ''),
                            'description': getattr(entry, 'summary', ''),
                            'published': pub_date,
                            'source': source_name
                        }
                        all_articles.append(article)
                
                except Exception as e:
                    print(f"     ⚠️  处理文章时出错: {e}")
                    continue
            
            # 添加延迟以避免过于频繁的请求
            time.sleep(1)
        
        except Exception as e:
            print(f"   ❌ 获取 {source_name} 时出错: {e}")
            continue
    
    # 按时间排序
    all_articles.sort(key=lambda x: x['published'], reverse=True)
    
    if all_articles:
        print()
        print(f"📊 找到 {len(all_articles)} 条符合条件的新闻:")
        print()
        
        for i, article in enumerate(all_articles, 1):
            print(f"{i}. 🕐 {article['published'].strftime('%H:%M')}")
            print(f"   📝 {article['title']}")
            print(f"   🏢 来源: {article['source']}")
            if article['link']:
                print(f"   🔗 {article['link']}")
            if article['description']:
                desc = article['description'].replace('<[^<]+?>', '').replace('\n', ' ')[:200] + "..."
                print(f"   📄 摘要: {desc}")
            print()
    else:
        print()
        print("🔍 在指定时间范围内未找到相关新闻")
        print()
        print("💡 提示: 可能是因为RSS源中的新闻发布时间不在今天早上6:00之后")
        print("   或者RSS源暂时不可用")
    
    # 显示历史记录中的总链接数
    history_file = "history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            if 'processed_urls' in history_data:
                total_links = len(history_data['processed_urls'])
                print(f"📈 系统总计已处理新闻链接: {total_links}")
            else:
                print("📈 无法统计已处理的新闻链接数量")
        except:
            print("📈 无法读取历史记录文件")

def get_recent_processed_links():
    """显示最近处理的链接（从history.json）"""
    history_file = "history.json"
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            if 'processed_urls' in history_data:
                processed_urls = history_data['processed_urls']
                
                print(f"\n📋 最近处理的20个链接:")
                print("-" * 40)
                
                # 显示最近的20个链接
                recent_urls = processed_urls[-20:] if len(processed_urls) > 20 else processed_urls
                
                for i, url in enumerate(recent_urls, 1):
                    print(f"{i:2d}. {url}")
                
                print(f"\n💡 总计已处理 {len(processed_urls)} 个链接")
        except Exception as e:
            print(f"⚠️  读取历史记录时出错: {e}")

if __name__ == "__main__":
    print("🔄 正在搜索从早上6:00到现在的新闻...")
    print()
    
    get_news_since_morning()
    get_recent_processed_links()
    
    print()
    print("💡 注意: 由于历史记录中没有时间戳信息，此脚本直接从RSS源获取最新的新闻")
    print("   以确定哪些新闻是在今天早上6:00之后发布的")