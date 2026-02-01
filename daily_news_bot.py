#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily News Bot - 全球情报与金融分析自动化脚本

功能：
1. 从国际主流RSS源抓取新闻（通过代理）
2. 调用DeepSeek大模型API进行深度分析
3. 发送到飞书群（使用webhook方式）

作者：Python高级工程师
"""

import feedparser
import requests
import json
import time
import logging
import random
from typing import List, Dict, Optional
from urllib.parse import urljoin
import os
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
from fake_useragent import UserAgent

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== 配置区域 ====================
# 请根据实际情况修改以下配置

# LLM API 配置 - 从环境变量读取
API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
BASE_URL = "https://api.deepseek.com"

# 智能代理配置 - 检查是否在GitHub Actions环境中
if os.environ.get('GITHUB_ACTIONS'):
    # 在GitHub Actions中，直接连接
    PROXIES = None
else:
    # 本地环境，使用代理
    PROXIES = {
        'http': 'http://127.0.0.1:7897',
        'https': 'http://127.0.0.1:7897'
    }

# RSS源列表（终极版本）
RSS_SOURCES = [
    # --- 1. 国际顶流 (BBC/NYT) ---
    "https://feeds.bbci.co.uk/news/world/rss.xml",  # BBC World
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",  # NYT World
    
    # --- 2. 华尔街/金融 (CNBC) ---
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",  # CNBC Finance

    # --- 3. 硅谷/科技 (TechCrunch) ---
    "https://techcrunch.com/feed/",  # TechCrunch AI & Startup

    # --- 4. 雅虎财经 (新增) ---
    "https://finance.yahoo.com/news/rssindex",  # Yahoo Finance

    # --- 5. 加密货币 (Crypto) ---
    "https://www.coindesk.com/arc/outboundfeeds/rss/",  # CoinDesk
    "https://cointelegraph.com/rss",  # Cointelegraph
    "https://crypto-slate.com/feed/",  # Crypto Slate

    # --- 6. 能源与战争 (Energy) ---
    "https://oilprice.com/rss/main",  # OilPrice.com

    # --- 7. 社交与黑客动向 (替代 Twitter/GitHub) ---
    # Hacker News (全球极客都在讨论什么，是 GitHub 最好的风向标)
    "https://news.ycombinator.com/rss",
    # Reddit WorldNews (全球网民最热议的突发事件)
    "https://www.reddit.com/r/worldnews/top/.rss?t=day",
    
    # --- 8. Reddit 视频聚合 (新增) ---
    "https://www.reddit.com/r/videos/top/.rss?t=day",  # Reddit 视频聚合 - 全球24小时内最热门的视频集合
    
    # --- 9. 亚洲/中国商业 (新增) ---
    "https://www.scmp.com/rss/2/feed",  # South China Morning Post (南华早报 - 中国商业版块)
    
    # --- 10. 学术/AI研究 (新增) ---
    "http://arxiv.org/rss/cs.AI",  # ArXiv AI Paper Daily (学术源)
    "https://mittechnologyreview.com/feed/",  # MIT Technology Review (科技趋势分析)
    
    # --- 11. 国内主流新闻源 (新增) ---
    "http://news.baidu.com/n?cmd=file&format=rss&tn=rss&sub=0",  # 百度新闻
    "http://rss.people.com.cn/GB/303140/index.xml",  # 人民网
    "http://www.xinhuanet.com/politics/news_politics.xml",  # 新华网 - 时政
    "http://www.chinanews.com/rss/scroll-news.xml",  # 中国新闻网
    "https://www.thepaper.cn/rss.jsp",  # 澎湃新闻
    "http://www.ce.cn/cysc/jg/zxbd/rss2.xml",  # 中国经济网
    "https://www.cls.cn/v3/highlights?app_id=70301d300f0f95a1&platform=pc",  # 财联社 (需要适配)
    
    # --- 12. 国内科技新闻 (新增) ---
    "https://www.zhihu.com/rss",  # 知乎每日精选
    "https://www.36kr.com/feed",  # 36氪
    "https://news.qq.com/rss/channels/finance/rss.xml",  # 腾讯财经
    "https://rss.sina.com.cn/news/china/focus15.xml",  # 新浪新闻-国内焦点

    # --- 13. 主要科技公司官网 (新增) ---
    "https://blog.google/rss/",  # Google Blog
    "https://openai.com/blog/rss/",  # OpenAI Blog
    "https://blogs.microsoft.com/feed/",  # Microsoft Blog
    "https://www.apple.com/newsroom/rss-feed.rss",  # Apple Newsroom
    "https://nvidianews.nvidia.com/rss.xml",  # NVIDIA Newsroom
    "https://about.meta.com/rss/feed/",  # Meta Newsroom

    # --- 14. 主流财经媒体 (新增) ---
    "https://feeds.reuters.com/reuters/topNews",  # Reuters Top News
    "https://feeds.reuters.com/reuters/businessNews",  # Reuters Business
    "https://feeds.reuters.com/reuters/technologyNews",  # Reuters Technology
    "https://bloomberg.com/feed",  # Bloomberg (可能需要适配)
    "https://www.wsj.com/xml/rss/3_7085.xml",  # Wall Street Journal (可能需要适配)

    # --- 15. 科技媒体 (新增) ---
    "https://www.theverge.com/rss/index.xml",  # The Verge
    "https://arstechnica.com/feed/",  # Ars Technica

    # --- 16. 投资机构和数据库 (新增) ---
    "https://www.cbinsights.com/blog/feed/",  # CB Insights
    "https://techcrunch.com/startups/",  # TechCrunch Startups
    "https://www.crunchbase.com/feed",  # Crunchbase (可能需要适配)

    # --- 17. AI研究机构 (新增) ---
    "https://stability.ai/rss",  # Stability AI
    "https://huggingface.co/blog/feed.xml",  # Hugging Face Blog

    # --- 18. 商业领袖和企业高管 (新增) ---
    "https://www.tesla.com/blog/rss",  # Tesla Blog
    "https://about.twitter.com/content/dam/about-twitter/company/news/rss-feeds/official-company-blog-rss.xml",  # Twitter Blog (X)
    "https://www.spacex.com/static/releases/feed.xml",  # SpaceX Releases

    # --- 19. 加密货币和区块链 (新增) ---
    "https://cointelegraph.com/feed",  # Cointelegraph
    "https://decrypt.co/feed",  # Decrypt
    "https://messari.io/feed.xml",  # Messari
    "https://theblock.co/rss",  # The Block

    # --- 20. 交易和投资平台 (新增) ---
    "https://www.binance.com/en/blog/rss",  # Binance Blog
    "https://blog.coinbase.com/feed",  # Coinbase Blog

    # --- 21. 区块链协议 (新增) ---
    "https://blog.ethereum.org/feed.xml",  # Ethereum Blog
    "https://polkadot.network/feed/",  # Polkadot Blog

    # --- 22. 金融和投资 (新增) ---
    "https://seekingalpha.com/feed.xml",  # Seeking Alpha
    "https://www.ft.com/?format=rss",  # Financial Times (可能需要适配)

    # --- 23. 亚马逊相关 (新增) ---
    "https://www.aboutamazon.com/news/rss-feed.xml",  # Amazon Newsroom

    # --- 24. 马斯克相关 (新增) ---
    "https://www.neuralink.com/blog.rss",  # Neuralink Blog
    "https://www.boringcompany.com/blog",  # The Boring Company Blog (可能需要适配)

    # --- 25. 其他AI公司 (新增) ---
    "https://www.anthropic.com/rss",  # Anthropic Blog
    "https://deepmind.google/rss/",  # DeepMind Blog
    "https://aws.amazon.com/blogs/aws/feed/",  # AWS Blog
    "https://www.amd.com/en/press-room/press-releases.rss",  # AMD Press Releases
]

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 缓存管理 ====================

def load_cache() -> set:
    """
    从history.json加载已处理的URL缓存
    """
    if os.path.exists('history.json'):
        try:
            with open('history.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('processed_urls', []))
        except Exception as e:
            logger.warning(f"加载缓存失败: {e}")
            return set()
    else:
        # 如果文件不存在，创建一个空的缓存文件
        save_cache(set())
        return set()

def save_cache(processed_urls: set):
    """
    保存已处理的URL到history.json
    """
    try:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump({'processed_urls': list(processed_urls)}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存缓存失败: {e}")

def send_to_feishu(message: str, max_retries: int = MAX_RETRIES) -> bool:
    """
    使用飞书webhook发送消息到群组
    
    Args:
        message: 要发送的消息内容
        max_retries: 最大重试次数
        
    Returns:
        发送是否成功
    """
    # 直接使用webhook方式发送
    return send_to_feishu_webhook(message, max_retries)


def send_to_feishu_webhook(message: str, max_retries: int = MAX_RETRIES) -> bool:
    """
    使用飞书webhook发送消息到群组（富文本格式）
    
    Args:
        message: 要发送的消息内容
        max_retries: 最大重试次数
        
    Returns:
        发送是否成功
    """
    # 从环境变量获取webhook URL，如果不存在则使用占位符
    webhook_url = os.environ.get('FEISHU_WEBHOOK_URL', '')
    # 准备消息内容（转换为适合富文本的格式）
    # 移除可能引起问题的特殊字符和格式，优化排版
    clean_message = message.replace('\ud83d', '').replace('\ude0a', '')  # 移除某些emoji
    clean_message = clean_message.replace('---', '\n──────\n')  # 只保留一条简洁的分隔线
    clean_message = clean_message.replace('####', '###')  # 统一标题层级
    clean_message = clean_message.replace('###', '\n● ')  # 将三级标题改为圆点
    clean_message = clean_message.replace('##', '\n◆ ')  # 将二级标题改为菱形符号
    clean_message = clean_message.replace('#', '\n★ ')  # 将一级标题改为星号

    # 构建富文本消息（使用interactive类型实现卡片效果）
    data = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "blue",
                "title": {
                    "content": "🌍 全球情报与金融分析日报",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": clean_message
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "🤖 DeepSeek-V3 智能分析系统 | 📅 " + time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                    ]
                }
            ]
        }
    }

    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }

    for attempt in range(max_retries):
        try:
            logger.info(f"正在发送消息到飞书webhook (尝试 {attempt + 1}/{max_retries})")
            response = requests.post(webhook_url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('StatusCode') == 0 or result.get('code') == 0:
                    logger.info("✅ 消息成功发送到飞书！")
                    return True
                else:
                    logger.error(f"飞书webhook返回错误: {result.get('msg') or result.get('message')}")
            else:
                logger.error(f"HTTP错误: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"发送飞书webhook消息异常 (尝试 {attempt + 1}): {e}")
        if attempt < max_retries - 1:
            time.sleep(RETRY_DELAY)
    
    logger.error("❌ 消息发送最终失败")
    return False


# ==================== 核心功能模块 ====================

def fetch_rss_feed(url: str, max_retries: int = MAX_RETRIES) -> Optional[feedparser.FeedParserDict]:
    """
    从RSS源抓取新闻，带重试机制和代理支持
    
    Args:
        url: RSS源URL
        max_retries: 最大重试次数
        
    Returns:
        feedparser解析结果或None
    """
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    
    # 智能延迟，避免请求过于频繁
    time.sleep(random.uniform(1.0, 3.0))
    
    # 初始化UserAgent
    ua = UserAgent()
    
    for attempt in range(max_retries):
        try:
            logger.info(f"正在抓取RSS源: {url} (尝试 {attempt + 1}/{max_retries})")
            
            # 使用更真实的请求头，模拟浏览器行为
            headers = {
                'User-Agent': ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # 使用代理抓取RSS（如果启用）
            response = requests.get(
                url, 
                proxies=PROXIES, 
                timeout=15,  # 增加超时时间
                headers=headers
            )
            
            # 根据HTTP状态码进行不同处理
            if response.status_code == 200:
                # 成功，解析RSS
                feed = feedparser.parse(response.content)
                logger.info(f"成功抓取 {len(feed.entries)} 条新闻")
                return feed
            elif response.status_code == 403:
                # 403错误：服务器拒绝访问，可能是反爬虫机制
                logger.warning(f"403错误 - 访问被拒绝: {url}")
                # 更换User-Agent再试
                headers['User-Agent'] = ua.random
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))  # 递增延迟
                continue
            elif response.status_code == 404:
                # 404错误：资源不存在
                logger.error(f"404错误 - RSS源不存在: {url}")
                return None  # 不重试，直接返回
            elif response.status_code == 429:
                # 429错误：请求过多
                logger.warning(f"429错误 - 请求频率过高: {url}")
                # 获取重试时间（如果有Retry-After头）
                retry_after = response.headers.get('Retry-After', 60)
                try:
                    delay = int(retry_after)
                except ValueError:
                    delay = 60  # 默认等待60秒
                if attempt < max_retries - 1:
                    time.sleep(delay * (attempt + 1))
                continue
            else:
                # 其他错误
                logger.warning(f"HTTP错误 {response.status_code}: {url}")
                if attempt < max_retries - 1:
                    time.sleep(3 * (attempt + 1))
                    
        except requests.exceptions.SSLError as e:
            logger.warning(f"SSL错误 (尝试 {attempt + 1}): {e}")
            # 尝试忽略SSL验证
            if attempt < max_retries - 1:
                try:
                    response = requests.get(
                        url, 
                        proxies=PROXIES, 
                        timeout=15,  # 增加超时时间
                        headers=headers,
                        verify=False  # 忽略SSL验证
                    )
                    if response.status_code == 200:
                        feed = feedparser.parse(response.content)
                        logger.info(f"成功抓取 {len(feed.entries)} 条新闻 (忽略SSL验证)")
                        return feed
                except Exception:
                    pass  # 继续重试
                time.sleep(5 * (attempt + 1))
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

def extract_news_items() -> List[Dict[str, str]]:
    """
    从多个RSS源提取新闻条目，并按重要性排序
    
    Returns:
        新闻条目列表，每个包含title, summary, link, importance_score
    """
    all_news = []
    seen_titles = set()  # 用于去重
    processed_urls = load_cache()  # 加载已处理的URL缓存
    
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
    
    for rss_url in RSS_SOURCES:
        feed = fetch_rss_feed(rss_url)
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
    
    # 更新缓存，添加新处理的URL
    for item in all_news:
        processed_urls.add(item['link'])
    save_cache(processed_urls)
    
    logger.info(f"总共提取到 {len(all_news)} 条唯一新闻，并按重要性排序")
    return all_news[:10]  # 最多处理10条新闻

def get_asset_price(asset_name: str) -> Optional[str]:
    """
    获取指定资产的实时价格（使用免费API）
    支持比特币、黄金、英伟达股票等
    """
    try:
        # 根据资产名称选择不同的API
        if asset_name.lower() in ['bitcoin', 'btc', '比特币']:
            # 使用CoinGecko API获取比特币价格
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10)
            if response.status_code == 200:
                data = response.json()
                price = data['bitcoin']['usd']
                return f"${price:,}"
        elif asset_name.lower() in ['ethereum', 'eth', '以太坊']:
            # 使用CoinGecko API获取以太坊价格
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd", timeout=10)
            if response.status_code == 200:
                data = response.json()
                price = data['ethereum']['usd']
                return f"${price:,}"
        elif asset_name.lower() in ['gold', '黄金']:
            # 使用贵金属API获取黄金价格（USD/盎司）
            response = requests.get("https://api.metals.live/v1/spot/gold", timeout=10)
            if response.status_code == 200:
                data = response.json()
                price = data['value']
                return f"${price:.2f}/oz"
        elif asset_name.lower() in ['nvidia', 'nvda', '英伟达']:
            # 使用Yahoo Finance API获取英伟达股票价格
            response = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/NVDA", timeout=10)
            if response.status_code == 200:
                data = response.json()
                price = data['chart']['result'][0]['meta']['regularMarketPrice']
                return f"${price:.2f}"
        elif asset_name.lower() in ['apple', 'aapl', '苹果']:
            # 使用Yahoo Finance API获取苹果股票价格
            response = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/AAPL", timeout=10)
            if response.status_code == 200:
                data = response.json()
                price = data['chart']['result'][0]['meta']['regularMarketPrice']
                return f"${price:.2f}"
        elif asset_name.lower() in ['s&p 500', 'sp500', '标普500']:
            # 使用Yahoo Finance API获取标普500价格
            response = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/SPY", timeout=10)
            if response.status_code == 200:
                data = response.json()
                price = data['chart']['result'][0]['meta']['regularMarketPrice']
                return f"${price:.2f}"
    except Exception as e:
        logger.warning(f"获取{asset_name}价格失败: {e}")
        return None

def analyze_news_with_llm(news_items: List[Dict[str, str]], report_type: str = 'daily') -> str:
    """
    调用LLM API对新闻进行深度分析（带去重逻辑、情绪评分、价格注入和图片信息）
    使用分批处理机制，避免一次性发送过多内容导致超时
    
    Args:
        news_items: 新闻条目列表
        report_type: 报告类型 ('morning', 'noon', 'evening', 'summary', 'daily')
        
    Returns:
        LLM生成的Markdown格式分析报告
    """
    if not news_items:
        return "今日无重要新闻更新。"
    
    # 将新闻列表按每30条一组进行拆分
    batch_size = 30
    batches = [news_items[i:i + batch_size] for i in range(0, len(news_items), batch_size)]
    
    # 为每个批次构建分析内容
    batch_analyses = []
    for batch_idx, batch in enumerate(batches):
        logger.info(f"正在处理第 {batch_idx + 1}/{len(batches)} 批次新闻 (共 {len(batch)} 条)")
        
        # 构建单个批次的新闻内容
        news_content = ""
        for i, item in enumerate(batch):
            # 检查新闻中是否包含需要价格注入的关键词
            title_lower = item['title'].lower()
            summary_lower = item['summary'].lower()
            price_info = ""
            
            # 检查是否包含相关资产关键词
            assets_to_check = ['bitcoin', 'btc', 'ethereum', 'eth', 'gold', 'nvidia', 'nvda', 'apple', 'aapl', 's&p 500', 'sp500']
            for asset in assets_to_check:
                if asset in title_lower or asset in summary_lower:
                    price = get_asset_price(asset)
                    if price:
                        price_info = f" (当前价格：{price})"
                    break  # 找到一个匹配就停止
            
            news_content += f"**ID**: {i+1}\n**标题**: {item['title']}{price_info}\n**摘要**: {item['summary']}\n**链接**: {item['link']}\n\n"
        
        # 为单个批次生成系统提示词
        SYSTEM_PROMPT = """你是一名顶级游资操盘手和宏观策略师。你的读者是时间宝贵的中国投资者/打工人。
你的任务是：**透过新闻表象，直接拆解利益链条，给出最冷血的判断。**

# Constraints
1. **详细分析**：全篇控制在 600 字左右，提供深入的分析和见解。
2. **通俗易懂**：使用简单明了的语言，避免复杂的箭头符号，让普通用户也能理解。
3. **格式严格**：必须遵守下方的 Markdown 格式。
4. **中国视角**：所有影响分析必须紧扣中国国运、A股/港股和打工人的钱袋子。
5. **严禁描述图片**：不要输出任何图片描述。

# Analysis Framework (Markdown Output)
请对筛选出的 Top 新闻按以下结构输出：

### [情绪分 | 分数] 新闻标题 (中文，加粗)

> [🔗 点击直达原新闻](新闻URL) | 来源：新闻Source

**核心要点**：一句话概括新闻的核心内容

**事件详情**：详细介绍发生了什么事情，涉及哪些关键人物、公司或组织，以及具体的时间、地点、数据等。

**深层解读**：深入分析这则新闻背后的动机和原因。为什么会出现这种情况？是出于商业考虑、政策驱动、市场竞争还是技术突破？解释清楚事件发生的根本原因。

**对中国的潜在影响**：
- **短期影响**：对中国经济、金融市场、相关行业或消费者的直接影响
- **长期影响**：对未来发展趋势、产业布局、国际地位等方面的深远影响

**对股市和投资的影响**：
- **可能受益的板块或股票**：列出可能因此受益的行业、公司或投资标的
- **可能受损的板块或股票**：指出可能面临负面影响的领域
- **投资策略建议**：基于此新闻，投资者应该如何调整策略

**未来展望**：预测这一事件可能带来的后续发展，以及我们应该如何应对。

**关联信息**：如果这则新闻与其他事件有关联，说明它们之间的联系。"""

        system_prompt = SYSTEM_PROMPT

        # 用户消息
        user_message = f"请分析以下新闻（共{len(batch)}条），并对重复话题进行合并，为每条新闻添加情绪评分和价格信息：\n\n{news_content}"
        
        # 调用DeepSeek API（使用OpenAI兼容格式）
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "deepseek-chat",  # DeepSeek V3.2的模型名称
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 4000  # 增加token限制以处理多条新闻
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"正在调用DeepSeek API进行第 {batch_idx + 1} 批次新闻分析 (尝试 {attempt + 1}/{MAX_RETRIES})")
                
                # DeepSeek API在中国境内，不需要代理
                response = requests.post(
                    f"{BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    proxies=None,  # 不使用代理访问DeepSeek API
                    timeout=(5, 120)  # 增加超时时间到120秒，连接5秒，读取120秒
                )
                
                if response.status_code == 200:
                    result = response.json()
                    analysis = result['choices'][0]['message']['content']
                    logger.info(f"第 {batch_idx + 1} 批次LLM分析完成")
                    batch_analyses.append(analysis)
                    break  # 成功后跳出重试循环
                else:
                    logger.warning(f"LLM API调用失败: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.warning(f"LLM API调用异常 (尝试 {attempt + 1}): {e}")
                
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
        else:
            # 如果所有重试都失败，添加简化版本
            logger.error(f"第 {batch_idx + 1} 批次LLM分析失败，返回简化版本")
            fallback_analysis = ""
            for i, item in enumerate(batch[:3], 1):
                fallback_analysis += f"### {i}. [点击直达：{item['title']}]({item['link']})\n"
                fallback_analysis += "- **📅 来源**: 国际媒体\n"
                fallback_analysis += f"- **📝 核心事实**: {item['summary'][:30]}...\n\n"
                fallback_analysis += "#### 📊 深度研报\n"
                fallback_analysis += "* **🇨🇳 对中国短期影响**: 待分析\n"
                fallback_analysis += "* **🔮 对中国长期影响**: 待分析\n"
                fallback_analysis += "* **📈 股市影响 (A股/港股/美股)**:\n"
                fallback_analysis += "    * *利好/利空板块*: 待分析\n"
                fallback_analysis += "    * *底层逻辑*: 待分析\n\n"
                fallback_analysis += "---\n"
            batch_analyses.append(fallback_analysis)
    
    # 如果有多批次，需要将各批次结果进行综合汇总
    if len(batch_analyses) > 1:
        logger.info(f"正在进行跨批次综合汇总 (共 {len(batch_analyses)} 个批次)")
        combined_analysis = "\n".join(batch_analyses)
        summary_prompt = f"""你是一个专业的新闻分析师。请将以下来自不同批次的新闻分析结果进行整合，去除重复内容，形成一份连贯的报告。要求保持原有的格式和结构。

{combined_analysis}"""

        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个专业的新闻分析师，负责整合多份新闻分析报告。"},
                {"role": "user", "content": summary_prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 4000
        }

        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"正在调用DeepSeek API进行跨批次综合汇总 (尝试 {attempt + 1}/{MAX_RETRIES})")
                
                response = requests.post(
                    f"{BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    proxies=None,
                    timeout=(5, 120)  # 增加超时时间
                )
                
                if response.status_code == 200:
                    result = response.json()
                    final_analysis = result['choices'][0]['message']['content']
                    logger.info("跨批次综合汇总完成")
                    return final_analysis
                else:
                    logger.warning(f"跨批次汇总API调用失败: {response.status_code} - {response.text}")
            except Exception as e:
                logger.warning(f"跨批次汇总API调用异常 (尝试 {attempt + 1}): {e}")
                
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
        else:
            logger.error("跨批次综合汇总失败，返回原始批次分析结果")
            return combined_analysis

    # 如果只有一个批次，直接返回
    return batch_analyses[0] if batch_analyses else "今日无重要新闻更新。"

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

def parse_sentiment_score(message: str) -> float:
    """
    从消息中解析整体情绪得分
    """
    import re
    # 查找类似 [🔥+8] 或 [❄️-8] 的模式
    pattern = r'\[(?:🔥|❄️|⚡|📉|📈)\s*([+-]?\d+)\]'
    matches = re.findall(pattern, message)
    if matches:
        scores = [int(score) for score in matches]
        # 返回平均值作为整体情绪得分
        return sum(scores) / len(scores) if scores else 0
    return 0

def main():
    """
    主函数 - 执行完整的新闻分析流程
    """
    logger.info("🚀 启动每日新闻机器人...")
    try:
        # 1. 抓取新闻
        news_items = extract_news_items()
        if not news_items:
            logger.warning("未获取到任何新闻，跳过分析")
            # 即使没有新闻也要记录日志
            logger.info("📊 抓取统计: 成功 0 条, 失败 0 条")
            return
        
        logger.info(f"📊 抓取统计: 成功 {len(news_items)} 条, 失败 0 条")
        
        # 2. LLM深度分析
        analysis_result = analyze_news_with_llm(news_items)
        sentiment_score = parse_sentiment_score(analysis_result)
        logger.info(f"📊 LLM评分明细: 情绪分 {sentiment_score}, 新闻数量 {len(news_items)}")
        
        # 3. 发送到飞书
        success = send_to_feishu(analysis_result)
        
        if success:
            logger.info("🎉 每日新闻分析任务完成！")
        else:
            logger.error("❌ 每日新闻分析任务失败")
            send_error_alert("日报发送失败，请检查飞书应用配置")
            
    except Exception as e:
        logger.exception(f"主函数执行异常: {e}")
        send_error_alert(f"机器人故障：{str(e)}，请主人检查！")

def send_error_alert(error_message: str, max_retries: int = MAX_RETRIES):
    """
    发送错误警报到飞书（使用webhook方式）
    """
    # 构建错误警报消息
    alert_msg = f"🚨 机器人故障警报\n\n错误详情：{error_message}\n\n请及时检查机器人状态！\n\nDeepSeek-V3 监控系统"
    
    # 使用webhook发送错误警报
    return send_to_feishu_webhook(alert_msg, max_retries)

# ==================== 主函数 ====================

if __name__ == "__main__":
    main()


