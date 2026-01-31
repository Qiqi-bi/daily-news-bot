#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取从早上6:00到当前时间的新闻摘要
"""

import json
import datetime
from datetime import timezone
import os

def get_news_from_history():
    """从历史记录中获取从早上6:00到当前时间的新闻"""
    
    # 获取当前时间
    now = datetime.datetime.now()
    today = now.date()
    
    # 构造早上6:00的时间
    morning_time = datetime.datetime.combine(today, datetime.time(6, 0))
    
    print(f"📰 从早上6:00到现在的新闻摘要")
    print("=" * 60)
    print(f"📅 时间范围: {morning_time.strftime('%Y-%m-%d %H:%M')} 到 {now.strftime('%Y-%m-%d %H:%M')}")
    print()
    
    # 尝试读取历史记录文件
    history_file = "history.json"
    if not os.path.exists(history_file):
        print("⚠️  历史记录文件不存在，无法获取过往新闻")
        print("💡 提示: 系统需要运行过新闻抓取程序才能生成历史记录")
        return
    
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        
        # 查找时间范围内的新闻
        relevant_news = []
        
        # 检查不同格式的历史数据
        if isinstance(history_data, dict):
            # 如果是字典格式，检查是否有news或articles字段
            if 'news' in history_data:
                articles = history_data['news']
            elif 'articles' in history_data:
                articles = history_data['articles']
            elif 'data' in history_data:
                articles = history_data['data']
            else:
                # 如果是按日期组织的数据
                articles = []
                for key, value in history_data.items():
                    if isinstance(value, list):
                        articles.extend(value)
                    elif isinstance(value, dict) and 'articles' in value:
                        articles.extend(value['articles'])
        
        elif isinstance(history_data, list):
            # 如果是列表格式
            articles = history_data
        else:
            print("⚠️  历史记录格式未知")
            return
        
        # 筛选时间范围内的新闻
        for article in articles:
            try:
                # 尝试解析发布时间
                pub_date_str = None
                if isinstance(article, dict):
                    # 检查可能的日期字段
                    for date_field in ['pubDate', 'published', 'date', 'time', 'publish_time']:
                        if date_field in article:
                            pub_date_str = article[date_field]
                            break
                
                if pub_date_str:
                    # 尝试解析日期字符串
                    try:
                        if isinstance(pub_date_str, str):
                            # 尝试多种日期格式
                            date_formats = [
                                '%Y-%m-%dT%H:%M:%SZ',
                                '%Y-%m-%d %H:%M:%S',
                                '%Y-%m-%d %H:%M',
                                '%a, %d %b %Y %H:%M:%S %z',
                                '%a, %d %b %Y %H:%M:%S',
                            ]
                            
                            pub_date = None
                            for fmt in date_formats:
                                try:
                                    pub_date = datetime.datetime.strptime(pub_date_str.split('.')[0], fmt)
                                    break
                                except ValueError:
                                    continue
                            
                            if pub_date is None:
                                # 如果标准格式都不匹配，尝试更灵活的方式
                                pub_date_str_clean = pub_date_str.replace('T', ' ').split('+')[0].split('.')[0]
                                try:
                                    pub_date = datetime.datetime.strptime(pub_date_str_clean, '%Y-%m-%d %H:%M:%S')
                                except ValueError:
                                    try:
                                        pub_date = datetime.datetime.strptime(pub_date_str_clean, '%Y-%m-%d %H:%M')
                                    except ValueError:
                                        continue
                        elif isinstance(pub_date_str, (int, float)):
                            # 如果是时间戳
                            pub_date = datetime.datetime.fromtimestamp(pub_date_str)
                        
                        # 检查是否在时间范围内
                        if morning_time <= pub_date <= now:
                            relevant_news.append((article, pub_date))
                    
                    except Exception as e:
                        print(f"⚠️  解析日期时出错: {e}")
                        continue
            
            except Exception as e:
                print(f"⚠️  处理文章时出错: {e}")
                continue
        
        # 按时间排序
        relevant_news.sort(key=lambda x: x[1])
        
        if relevant_news:
            print(f"📊 找到 {len(relevant_news)} 条相关新闻:")
            print()
            
            for i, (article, pub_date) in enumerate(relevant_news, 1):
                print(f"{i}. 🕐 {pub_date.strftime('%H:%M')}")
                
                # 获取标题
                title = "无标题"
                if isinstance(article, dict):
                    for title_field in ['title', 'headline', 'subject']:
                        if title_field in article:
                            title = article[title_field]
                            break
                    # 清理标题
                    title = str(title).strip()
                    if len(title) > 100:
                        title = title[:97] + "..."
                
                print(f"   📝 {title}")
                
                # 获取链接
                link = ""
                if isinstance(article, dict):
                    for link_field in ['link', 'url', 'href', 'source_url']:
                        if link_field in article:
                            link = article[link_field]
                            break
                
                if link:
                    print(f"   🔗 {link}")
                
                # 获取来源
                source = ""
                if isinstance(article, dict):
                    for source_field in ['source', 'site', 'website', 'media']:
                        if source_field in article:
                            source = article[source_field]
                            break
                
                if source:
                    print(f"   🏢 来源: {source}")
                
                print()
        else:
            print("🔍 在指定时间范围内未找到相关新闻")
            print()
            print("💡 提示: 系统可能尚未在此期间运行新闻抓取程序")
    
    except FileNotFoundError:
        print(f"⚠️  未找到历史记录文件: {history_file}")
    except json.JSONDecodeError:
        print(f"⚠️  历史记录文件格式错误: {history_file}")
    except Exception as e:
        print(f"⚠️  读取历史记录时出错: {e}")

def get_recent_processed_links():
    """获取最近处理的链接（从get_daily_news.py的逻辑）"""
    history_file = "history.json"
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            total_links = 0
            if isinstance(history_data, dict):
                # 统计所有文章数量
                if 'news' in history_data and isinstance(history_data['news'], list):
                    total_links = len(history_data['news'])
                elif 'articles' in history_data and isinstance(history_data['articles'], list):
                    total_links = len(history_data['articles'])
                else:
                    # 尝试统计嵌套结构中的文章数
                    for key, value in history_data.items():
                        if isinstance(value, list):
                            total_links += len(value)
                        elif isinstance(value, dict) and 'articles' in value:
                            total_links += len(value['articles'])
            elif isinstance(history_data, list):
                total_links = len(history_data)
            
            print(f"📈 系统总计已处理新闻链接: {total_links}")
        except:
            print("📈 无法统计已处理的新闻链接数量")

if __name__ == "__main__":
    print("🔄 正在搜索从早上6:00到现在的新闻...")
    print()
    
    get_news_from_history()
    print()
    get_recent_processed_links()
    
    print()
    print("💡 提示: 如果没有找到相关新闻，可能是因为系统在此期间没有运行新闻抓取程序")
    print("   或者历史记录文件中没有对应时间段的数据")