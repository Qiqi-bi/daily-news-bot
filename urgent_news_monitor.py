#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紧急新闻监控机器人 - 高频监控重要事件脚本

功能：
1. 每30分钟从RSS源抓取最新新闻
2. 快速调用DeepSeek大模型API进行情绪评分
3. 只有当Abs(情绪分) >= 9（极度重要）时，才触发推送
4. 平时不打扰，一旦响铃，必是大事

作者：Python高级工程师
"""

import feedparser
import requests
import json
import time
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin
import os
import re

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

# RSS源列表（紧急监控专用，使用完整的新闻源列表）
URGENT_RSS_SOURCES = [
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
                "template": "red",  # 紧急事件使用红色标题
                "title": {
                    "content": "🚨 全球紧急事件警报",
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
            logger.info(f"正在发送紧急消息到飞书webhook (尝试 {attempt + 1}/{max_retries})")
            response = requests.post(webhook_url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('StatusCode') == 0 or result.get('code') == 0:
                    logger.info("🚨 紧急消息成功发送到飞书！")
                    return True
                else:
                    logger.error(f"飞书webhook返回错误: {result.get('msg') or result.get('message')}")
            else:
                logger.error(f"HTTP错误: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"发送飞书webhook消息异常 (尝试 {attempt + 1}): {e}")
        if attempt < max_retries - 1:
            time.sleep(RETRY_DELAY)
    
    logger.error("❌ 紧急消息发送最终失败")
    return False

def send_error_alert(error_message: str, max_retries: int = MAX_RETRIES):
    """
    发送错误警报到飞书（使用webhook方式）
    """
    # 构建错误警报消息
    alert_msg = f"🚨 机器人故障警报\n\n错误详情：{error_message}\n\n请及时检查机器人状态！\n\nDeepSeek-V3 监控系统"
    
    # 从环境变量获取webhook URL，如果不存在则使用占位符
    webhook_url = os.environ.get('FEISHU_WEBHOOK_URL', '')
    # 构建富文本消息（使用interactive类型实现卡片效果）
    data = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "red",  # 紧急事件使用红色标题
                "title": {
                    "content": "🚨 机器人故障警报",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": alert_msg
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "🤖 DeepSeek-V3 监控系统 | 📅 " + time.strftime("%Y-%m-%d %H:%M:%S")
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
            logger.info(f"正在发送错误警报到飞书webhook (尝试 {attempt + 1}/{max_retries})")
            response = requests.post(webhook_url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('StatusCode') == 0 or result.get('code') == 0:
                    logger.info("🚨 错误警报成功发送到飞书！")
                    return True
                else:
                    logger.error(f"飞书webhook返回错误: {result.get('msg') or result.get('message')}")
            else:
                logger.error(f"HTTP错误: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"发送飞书webhook错误警报异常 (尝试 {attempt + 1}): {e}")
        if attempt < max_retries - 1:
            time.sleep(RETRY_DELAY)
    logger.error("❌ 错误警报发送失败")
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
    for attempt in range(max_retries):
        try:
            logger.info(f"正在抓取RSS源: {url} (尝试 {attempt + 1}/{max_retries})")
            
            # 使用代理抓取RSS（如果启用）
            response = requests.get(
                url, 
                proxies=PROXIES, 
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            response.raise_for_status()
            
            # 解析RSS
            feed = feedparser.parse(response.content)
            logger.info(f"成功抓取 {len(feed.entries)} 条新闻")
            return feed
            
        except Exception as e:
            logger.warning(f"抓取RSS失败 (尝试 {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"RSS抓取最终失败: {url}")
                return None
    
    return None

def extract_urgent_news_items() -> List[Dict[str, str]]:
    """
    从多个RSS源提取紧急新闻条目（只取最新的5条）
    
    Returns:
        新闻条目列表，每个包含title, summary, link
    """
    all_news = []
    seen_titles = set()  # 用于去重
    processed_urls = load_cache()  # 加载已处理的URL缓存
    
    for rss_url in URGENT_RSS_SOURCES:
        feed = fetch_rss_feed(rss_url)
        if not feed or not feed.entries:
            continue
            
        # 只取最新的5条新闻
        for entry in feed.entries[:5]:
            title = entry.get('title', '').strip()
            summary = entry.get('summary', '').strip()
            link = entry.get('link', '')
            
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
            
            all_news.append({
                'title': title,
                'summary': summary,
                'link': link
            })
    
    # 更新缓存，添加新处理的URL
    for item in all_news:
        processed_urls.add(item['link'])
    save_cache(processed_urls)
    
    logger.info(f"总共提取到 {len(all_news)} 条唯一紧急新闻")
    return all_news[:5]  # 最多处理5条紧急新闻

def analyze_urgent_news_with_llm(news_items: List[Dict[str, str]]) -> tuple:
    """
    调用LLM API对紧急新闻进行快速情绪评分
    
    Args:
        news_items: 新闻条目列表
        
    Returns:
        (分析结果, 情绪分数列表)
    """
    if not news_items:
        return "暂无紧急新闻。", []
    
    # 构建新闻内容
    news_content = ""
    for i, item in enumerate(news_items):
        news_content += f"**ID**: {i+1}\n**标题**: {item['title']}\n**摘要**: {item['summary']}\n**链接**: {item['link']}\n\n"
    
    # 紧急监控的系统提示词 - 专注快速情绪评分
    system_prompt = """你是一名顶级游资操盘手和宏观策略师。你的读者是时间宝贵的中国投资者/打工人。
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

    # 用户消息
    user_message = f"请快速分析以下新闻的情绪倾向，并为每条新闻添加情绪评分（只分析最重要的新闻）：\n\n{news_content}"
    
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
        "max_tokens": 2000  # 减少token限制以加快响应
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"正在调用DeepSeek API进行紧急新闻分析 (尝试 {attempt + 1}/{MAX_RETRIES})")
            
            # DeepSeek API在中国境内，不需要代理
            response = requests.post(
                f"{BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                proxies=None,  # 不使用代理访问DeepSeek API
                timeout=30  # 减少超时时间以加快响应
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result['choices'][0]['message']['content']
                
                # 提取情绪分数
                sentiment_scores = []
                pattern = r'\[(?:🔥|❄️|⚡|📉|📈)\s*([+-]?\d+)\]'
                matches = re.findall(pattern, analysis)
                for match in matches:
                    try:
                        score = int(match)
                        sentiment_scores.append(score)
                    except ValueError:
                        continue
                        
                logger.info(f"LLM分析完成，检测到情绪分数: {sentiment_scores}")
                return analysis, sentiment_scores
            else:
                logger.warning(f"LLM API调用失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.warning(f"LLM API调用异常 (尝试 {attempt + 1}): {e}")
            
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    
    # 如果LLM调用失败，返回简化版本
    logger.error("LLM分析失败，返回简化版本")
    fallback_analysis = ""
    sentiment_scores = []
    for i, item in enumerate(news_items[:3], 1):
        fallback_analysis += f"### 1. [点击直达：{item['title']}]({item['link']})\n"
        fallback_analysis += f"- **📝 核心事实**: {item['summary'][:30]}...\n"
        fallback_analysis += "- **📊 情绪评分**：0 (待分析)\n"
        fallback_analysis += "- **🌍 影响范围**：待评估\n\n"
        fallback_analysis += "---\n"
    
    return fallback_analysis, sentiment_scores

def check_urgent_threshold(sentiment_scores: List[int]) -> bool:
    """
    检查是否达到紧急推送阈值
    
    Args:
        sentiment_scores: 情绪分数列表
        
    Returns:
        是否达到推送阈值
    """
    for score in sentiment_scores:
        if abs(score) >= 9:  # 只有当情绪分绝对值>=9时才推送
            logger.info(f"✅ 检测到高情绪分新闻: {score}，触发紧急推送")
            return True
    logger.info(f"ℹ️ 情绪分未达到阈值: {sentiment_scores}，保持静默")
    return False

def main():
    """
    主函数 - 执行紧急新闻监控流程
    """
    logger.info("🚨 启动紧急新闻监控机器人...")
    try:
        # 1. 抓取紧急新闻
        news_items = extract_urgent_news_items()
        if not news_items:
            logger.info("未获取到任何紧急新闻，结束本次监控")
            return
        
        # 2. LLM快速情绪评分
        analysis_result, sentiment_scores = analyze_urgent_news_with_llm(news_items)
        
        # 3. 检查是否达到推送阈值
        if check_urgent_threshold(sentiment_scores):
            # 4. 推送到飞书
            success = send_to_feishu(analysis_result)
            if success:
                logger.info("🚨 紧急新闻推送完成！")
            else:
                logger.error("❌ 紧急新闻推送失败")
                send_error_alert("紧急新闻推送失败，请检查飞书应用配置")
        else:
            logger.info("⚠️ 情绪分未达到推送阈值，保持静默")
            
    except Exception as e:
        logger.exception(f"紧急监控主函数执行异常: {e}")
        send_error_alert(f"紧急监控机器人故障：{str(e)}，请主人检查！")

if __name__ == "__main__":
    main()