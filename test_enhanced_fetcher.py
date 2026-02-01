#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强版RSS采集器
"""

import asyncio
import os
from enhanced_rss_fetcher import EnhancedRSSFetcher

async def test_enhanced_fetcher():
    """
    测试增强版RSS采集器的功能
    """
    print("🧪 开始测试增强版RSS采集器...")
    
    # 从环境变量获取API密钥
    api_keys = {
        'MARKETAUX_API_KEY': os.environ.get('MARKETAUX_API_KEY', ''),
        'POLYGON_API_KEY': os.environ.get('POLYGON_API_KEY', '')
    }
    
    # 创建采集器实例
    fetcher = EnhancedRSSFetcher(api_keys)
    
    print("🔍 执行多层采集策略...")
    
    # 执行采集
    all_articles = await fetcher.fetch_all()
    
    print(f"✅ 采集完成，共获取 {len(all_articles)} 篇文章")
    
    # 显示前几篇文章的信息
    for i, article in enumerate(all_articles[:5]):
        print(f"\n📰 文章 {i+1}:")
        print(f"   标题: {article.get('title', 'N/A')}")
        print(f"   链接: {article.get('link', 'N/A')}")
        print(f"   来源: {article.get('source', 'N/A')}")
        print(f"   发布时间: {article.get('published', 'N/A')}")
        
    # 测试去重功能
    print("\n🔄 测试去重功能...")
    unique_articles = fetcher.deduplicate_articles(all_articles)
    print(f"去重前: {len(all_articles)} 篇, 去重后: {len(unique_articles)} 篇")
    
    # 显示去重后的文章
    print("\n📋 去重后的文章:")
    for i, article in enumerate(unique_articles[:5]):
        print(f"\n📰 文章 {i+1}:")
        print(f"   标题: {article.get('title', 'N/A')}")
        print(f"   链接: {article.get('link', 'N/A')}")
        print(f"   来源: {article.get('source', 'N/A')}")
        
    print(f"\n🎯 测试完成！共获取 {len(unique_articles)} 篇不重复的文章")

if __name__ == "__main__":
    asyncio.run(test_enhanced_fetcher())