#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced News Fetcher - 改进版新闻抓取器
包含更完善的错误处理、请求频率控制和反爬虫对策
"""

import feedparser
import requests
import json
import time
import logging
import random
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import os
from collections import defaultdict

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RateLimiter:
    """请求频率限制器"""
    def __init__(self):
        self.last_request_time = defaultdict(float)
        self.request_count = defaultdict(int)
        self.time_window = 60  # 60秒窗口
    
    def can_make_request(self, domain):
        """检查是否可以在指定域名上发起请求"""
        current_time = time.time()
        
        # 清理过期的请求记录
        for dom in list(self.last_request_time.keys()):
            if current_time - self.last_request_time[dom] > self.time_window:
                del self.last_request_time[dom]
                del self.request_count[dom]
        
        # 检查请求频率
        if domain in self.request_count:
            # 每分钟最多10次请求
            if self.request_count[domain] >= 10:
                return False
        
        return True
    
    def record_request(self, domain):
        """记录请求"""
        current_time = time.time()
        self.last_request_time[domain] = current_time
        self.request_count[domain] += 1

class ProxyPool:
    """代理池管理"""
    def __init__(self):
        # 可以从外部配置文件加载代理列表
        self.proxies = [
            {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'},  # 示例代理
            {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'},  # 示例代理
            # 更多代理...
        ]
        self.current_index = 0
    
    def get_next_proxy(self):
        """获取下一个可用代理"""
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy

# 全局实例
rate_limiter = RateLimiter()
proxy_pool = ProxyPool()

def fetch_with_multiple_methods(url: str, headers: dict = None) -> Optional[requests.Response]:
    """
    使用多种方法尝试获取内容
    """
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    methods = [
        # 方法1: 标准请求
        lambda h: requests.get(url, headers=h, timeout=15),
        
        # 方法2: 模拟浏览器
        lambda h: requests.get(url, headers={
            **h,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }, timeout=15),
        
        # 方法3: 移动端模拟
        lambda h: requests.get(url, headers={
            **h,
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
            'Accept': '*/*',
        }, timeout=15)
    ]
    
    for i, method in enumerate(methods):
        try:
            response = method(headers.copy())
            if response.status_code == 200:
                return response
            elif response.status_code in [403, 429]:
                # 这些错误值得尝试其他方法
                continue
        except Exception:
            continue
    
    return None

def enhanced_fetch_rss_feed(url: str, max_retries: int = 5, use_proxy: bool = False) -> Optional[feedparser.FeedParserDict]:
    """
    增强版RSS抓取函数，集成了所有改进措施
    
    Args:
        url: RSS源URL
        max_retries: 最大重试次数
        use_proxy: 是否使用代理
        
    Returns:
        feedparser解析结果或None
    """
    domain = urlparse(url).netloc
    
    # 检查请求频率限制
    if not rate_limiter.can_make_request(domain):
        logger.info(f"达到 {domain} 的请求频率限制，等待...")
        time.sleep(60)
    
    # 智能延迟，避免请求过于规律
    delay = random.uniform(1.0, 3.0)
    time.sleep(delay)
    
    # 记录请求
    rate_limiter.record_request(domain)
    
    for attempt in range(max_retries):
        try:
            logger.info(f"正在抓取RSS源: {url} (尝试 {attempt + 1}/{max_retries})")
            
            # 尝试多种请求方法
            response = fetch_with_multiple_methods(url)
            
            # 如果启用了代理且初始请求失败，尝试使用代理
            if not response and use_proxy:
                proxy = proxy_pool.get_next_proxy()
                if proxy:
                    logger.info(f"使用代理 {proxy} 重新请求")
                    response = fetch_with_multiple_methods(url)
            
            if response and response.status_code == 200:
                feed = feedparser.parse(response.content)
                logger.info(f"成功抓取 {len(feed.entries)} 条新闻")
                return feed
            elif response and response.status_code == 404:
                # 404错误：资源不存在，不重试
                logger.error(f"404错误 - RSS源不存在: {url}")
                return None
            elif response and response.status_code == 403:
                # 403错误：服务器拒绝访问
                logger.warning(f"403错误 - 访问被拒绝: {url}")
                if attempt < max_retries - 1:
                    # 更换User-Agent再试
                    time.sleep(5 * (attempt + 1))
                continue
            elif response and response.status_code == 429:
                # 429错误：请求过多
                logger.warning(f"429错误 - 请求频率过高: {url}")
                # 获取重试时间（如果有Retry-After头）
                retry_after = response.headers.get('Retry-After', 60)
                try:
                    delay = int(retry_after)
                except ValueError:
                    delay = 60  # 默认等待60秒
                if attempt < max_retries - 1:
                    logger.info(f"等待 {delay} 秒后重试...")
                    time.sleep(delay * (attempt + 1))
                continue
            else:
                # 其他错误
                status_code = response.status_code if response else 'N/A'
                logger.warning(f"HTTP错误 {status_code}: {url}")
                if attempt < max_retries - 1:
                    time.sleep(3 * (attempt + 1))
                    
        except requests.exceptions.ConnectionError:
            logger.warning(f"连接错误 (尝试 {attempt + 1}): {url}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
        except requests.exceptions.Timeout:
            logger.warning(f"请求超时 (尝试 {attempt + 1}): {url}")
            if attempt < max_retries - 1:
                time.sleep(10 * (attempt + 1))
        except Exception as e:
            logger.warning(f"其他错误 (尝试 {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(3 * (attempt + 1))
    
    logger.error(f"RSS抓取最终失败: {url}")
    return None

def enhanced_extract_news_items(rss_sources: List[str]) -> List[Dict[str, str]]:
    """
    从多个RSS源提取新闻条目，并按重要性排序
    
    Args:
        rss_sources: RSS源列表
        
    Returns:
        新闻条目列表，每个包含title, summary, link, importance_score
    """
    all_news = []
    seen_titles = set()  # 用于去重
    processed_urls = set()  # 临时存储本次运行处理的URL
    
    # 定义RSS源权重，权威性越高的源权重越大
    source_weights = {
        "https://feeds.bbci.co.uk/news/world/rss.xml": 1.0,  # BBC World
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml": 1.0,  # NYT World
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664": 0.9,  # CNBC Finance
        "https://techcrunch.com/feed/": 0.8,  # TechCrunch AI & Startup
        "https://finance.yahoo.com/news/rssindex": 0.8,  # Yahoo Finance
        "https://www.coindesk.com/arc/outboundfeeds/rss/": 0.7,  # CoinDesk
        "https://oilprice.com/rss/main": 0.7,  # OilPrice.com
        "https://news.ycombinator.com/rss": 0.7,  # Hacker News
        "https://www.reddit.com/r/worldnews/top/.rss?t=day": 0.6,  # Reddit WorldNews
        "https://www.reddit.com/r/videos/top/.rss?t=day": 0.5,  # Reddit 视频聚合
        "https://www.scmp.com/rss/2/feed": 0.8,  # South China Morning Post
        "http://arxiv.org/rss/cs.AI": 0.6,  # ArXiv AI Paper Daily
        "http://news.baidu.com/n?cmd=file&format=rss&tn=rss&sub=0": 0.7,  # 百度新闻
        "http://rss.people.com.cn/GB/303140/index.xml": 0.9,  # 人民网
        "http://www.xinhuanet.com/politics/news_politics.xml": 0.9,  # 新华网 - 时政
        "http://www.chinanews.com/rss/scroll-news.xml": 0.7,  # 中国新闻网
        "https://www.thepaper.cn/rss.jsp": 0.6,  # 澎湃新闻
        "https://www.cls.cn/v3/highlights?app_id=70301d300f0f95a1&platform=pc": 0.7,  # 财联社
        "https://www.zhihu.com/rss": 0.5,  # 知乎每日精选
        "https://www.36kr.com/feed": 0.6,  # 36氪
        "https://news.qq.com/rss/channels/finance/rss.xml": 0.7,  # 腾讯财经
        "https://rss.sina.com.cn/news/china/focus15.xml": 0.7,  # 新浪新闻-国内焦点
    }
    
    for rss_url in rss_sources:
        feed = enhanced_fetch_rss_feed(rss_url, use_proxy=True)
        if not feed or not feed.entries:
            continue
            
        for entry in feed.entries[:5]:  # 每个源最多取5条
            title = entry.get('title', '').strip()
            summary = entry.get('summary', '').strip()
            link = entry.get('link', '')
            published_time = entry.get('published_parsed', None)
            
            # 检查URL是否已处理过
            if link in processed_urls:
                continue
            
            # 去重检查
            if not title or title in seen_titles:
                continue
                
            seen_titles.add(title)
            
            # 清理summary中的HTML标签
            import re
            summary = re.sub(r'<[^>]+>', '', summary)
            summary = summary[:200] + '...' if len(summary) > 200 else summary
            
            # 计算新闻重要性分数
            importance_score = calculate_importance_score(title, summary, rss_url, published_time, source_weights)
            
            all_news.append({
                'title': title,
                'summary': summary,
                'link': link,
                'importance_score': importance_score
            })
    
    # 按重要性分数降序排序
    all_news.sort(key=lambda x: x['importance_score'], reverse=True)
    
    logger.info(f"总共提取到 {len(all_news)} 条唯一新闻，并按重要性排序")
    return all_news[:10]  # 最多处理10条新闻

def calculate_importance_score(title: str, summary: str, source_url: str, published_time, source_weights: dict) -> float:
    """
    计算新闻重要性分数
    
    Args:
        title: 新闻标题
        summary: 新闻摘要
        source_url: 新闻来源URL
        published_time: 发布时间
        source_weights: 来源权重字典
    
    Returns:
        重要性分数 (0-10)
    """
    score = 0.0
    
    # 1. 来源权重 (基础分数)
    base_weight = source_weights.get(source_url, 0.5)  # 默认权重0.5
    score += base_weight * 4  # 权重占比40%
    
    # 2. 标题关键词分析 (时效性、紧急性、影响力)
    title_lower = title.lower()
    urgency_keywords = ['突发', '紧急', '警告', '危机', '暴跌', '暴涨', '战', '冲突', '制裁', '政策', '央行', '利率', 'gdp', '就业', '通胀']
    financial_keywords = ['经济', '股市', '基金', '债券', '美元', '人民币', '黄金', '石油', '比特币', 'ai', '科技', '公司', '财报']
    china_keywords = ['中国', 'chinese', 'beijing', 'shanghai', 'hk', '港', 'a股', '人民币', 'cny', '贸易', '中美', '美中']
    
    # 检查紧急关键词
    for keyword in urgency_keywords:
        if keyword in title_lower:
            score += 1.0  # 每个紧急关键词+1分
    
    # 检查金融关键词
    for keyword in financial_keywords:
        if keyword in title_lower:
            score += 0.5  # 每个金融关键词+0.5分
    
    # 检查中国相关关键词
    for keyword in china_keywords:
        if keyword in title_lower:
            score += 1.0  # 每个中国相关关键词+1分
    
    # 3. 内容长度 (更长的内容可能更重要)
    content_length = len(title) + len(summary)
    if content_length > 200:
        score += 1.0
    elif content_length > 100:
        score += 0.5
    
    # 4. 时间因素 (如果是今天发布的新闻，增加分数)
    import datetime
    if published_time:
        pub_date = datetime.datetime(*published_time[:6])
        now = datetime.datetime.now()
        hours_diff = (now - pub_date).total_seconds() / 3600
        if hours_diff <= 24:  # 24小时内发布的新闻
            score += 1.0
        elif hours_diff <= 48:  # 48小时内发布的新闻
            score += 0.5
    
    # 5. 标题长度和特征 (标题长度适中且包含数字或符号可能更重要)
    if 30 < len(title) < 100:  # 标题长度适中
        score += 0.5
    if ':' in title or '-' in title:  # 包含分隔符
        score += 0.3
    if any(char.isdigit() for char in title):  # 包含数字
        score += 0.2
    
    return min(score, 10.0)  # 限制最大分数为10

def main():
    """
    主函数 - 演示增强版新闻抓取器的使用
    """
    logger.info("🚀 启动增强版新闻抓取器...")
    
    # RSS源列表
    RSS_SOURCES = [
        "https://feeds.bbci.co.uk/news/world/rss.xml",  # BBC World
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",  # NYT World
        "https://techcrunch.com/feed/",  # TechCrunch AI & Startup
        "http://news.baidu.com/n?cmd=file&format=rss&tn=rss&sub=0",  # 百度新闻
    ]
    
    try:
        # 抓取新闻
        news_items = enhanced_extract_news_items(RSS_SOURCES)
        logger.info(f"成功提取 {len(news_items)} 条新闻")
        
        # 输出前几条新闻作为示例
        for i, item in enumerate(news_items[:3]):
            print(f"\n{i+1}. {item['title']}")
            print(f"   重要性分数: {item['importance_score']:.2f}")
            print(f"   链接: {item['link']}")
            print(f"   摘要: {item['summary'][:100]}...")
        
    except Exception as e:
        logger.exception(f"主函数执行异常: {e}")

if __name__ == "__main__":
    main()