#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紧急新闻监控机器人 - 高频监控重要事件脚本

功能：
1. 每30分钟从RSS源抓取最新新闻
2. 快速调用DeepSeek大模型API进行情绪评分
3. 只有当Abs(情绪分) >= 8（极度重要）时，才触发推送
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

# LLM API 配置 - 优先从环境变量读取，如果不存在则使用默认值
API_KEY = os.environ.get('DEEPSEEK_API_KEY', 'sk-1034e8c1dad248ea90ff08fddf2b5bd5')
BASE_URL = "https://api.deepseek.com"

# 飞书应用认证配置
APP_ID = os.environ.get('LARK_APP_ID', 'cli_a9f6280dd5389bd8')
APP_SECRET = os.environ.get('LARK_APP_SECRET', 'VHN4Eag0koh7rwEkKXeHSgHzLnH1140x')

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

# RSS源列表（紧急监控专用，只监控最重要的源）
URGENT_RSS_SOURCES = [
    # --- 顶级国际新闻 ---
    "https://feeds.bbci.co.uk/news/world/rss.xml",  # BBC World
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",  # NYT World
    
    # --- 金融市场 ---
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",  # CNBC Finance

    # --- 重大事件 ---
    "https://www.reddit.com/r/worldnews/top/.rss?t=day",  # Reddit WorldNews - 全球网民最热议的突发事件
    
    # --- 亚洲/中国 ---
    "https://www.scmp.com/rss/2/feed",  # South China Morning Post (南华早报 - 中国商业版块)
    
    # --- 国内主流新闻源 (新增) ---
    "http://news.baidu.com/n?cmd=file&format=rss&tn=rss&sub=0",  # 百度新闻
    "http://rss.people.com.cn/GB/303140/index.xml",  # 人民网
    "http://www.xinhuanet.com/politics/news_politics.xml",  # 新华网 - 时政
    "http://www.chinanews.com/rss/scroll-news.xml",  # 中国新闻网
    "https://www.thepaper.cn/rss.jsp",  # 澎湃新闻
    "http://www.ce.cn/cysc/jg/zxbd/rss2.xml",  # 中国经济网
    
    # --- 国内科技新闻 (新增) ---
    "https://www.36kr.com/feed",  # 36氪
    "https://news.qq.com/rss/channels/finance/rss.xml",  # 腾讯财经
    "https://rss.sina.com.cn/news/china/focus15.xml",  # 新浪新闻-国内焦点
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

# ==================== 飞书应用认证 ====================

def get_access_token() -> str:
    """
    获取飞书访问令牌
    """
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }
    data = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }

    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"正在获取飞书访问令牌 (尝试 {attempt + 1}/{MAX_RETRIES})")
            response = requests.post(url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    access_token = result.get('tenant_access_token')
                    logger.info("✅ 成功获取飞书访问令牌")
                    return access_token
                else:
                    logger.error(f"获取访问令牌失败: {result.get('msg')}")
            else:
                logger.error(f"HTTP错误: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"获取访问令牌异常 (尝试 {attempt + 1}): {e}")
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    return ""

def send_to_feishu(message: str, max_retries: int = MAX_RETRIES) -> bool:
    """
    使用飞书应用认证发送消息到群组（支持表格等的丰富格式）
    
    Args:
        message: 要发送的消息内容
        max_retries: 最大重试次数
        
    Returns:
        发送是否成功
    """
    # 获取访问令牌
    access_token = get_access_token()
    if not access_token:
        logger.error("❌ 无法获取访问令牌，消息发送失败")
        return False

    # 检测是否包含表格格式，如果是则使用card格式发送
    contains_table = '|' in message and '-' in message

    # 先尝试发送到群组，如果失败再尝试发送给用户
    targets = []
    chat_id = os.environ.get('LARK_CHAT_ID', '')
    user_id = os.environ.get('LARK_USER_ID', '')
    
    if chat_id:
        targets.append(('chat_id', chat_id))
    if user_id:
        targets.append(('user_id', user_id))
    # 如果都没有设置，默认尝试发送给用户
    if not chat_id and not user_id:
        targets.append(('user_id', ''))

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {access_token}"
    }

    for receive_id_type, receive_id in targets:
        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
        
        # 根据内容类型选择消息格式
        if contains_table:
            # 如果包含表格，构建更复杂的卡片消息
            data = {
                "receive_id": receive_id,
                "msg_type": "interactive",
                "content": json.dumps({
                    "config": {
                        "wide_screen_mode": True,
                        "update_multi": False,
                        "enable_forward": True
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
                            "content": message
                        },
                        {
                            "tag": "hr"
                        },
                        {
                            "tag": "action",
                            "actions": [
                                {
                                    "tag": "button",
                                    "text": {
                                        "content": "查看详情",
                                        "tag": "plain_text"
                                    },
                                    "type": "danger",  # 紧急按钮样式
                                    "value": {}
                                }
                            ]
                        }
                    ]
                })
            }
        else:
            # 普通消息格式
            data = {
                "receive_id": receive_id,
                "msg_type": "interactive",
                "content": json.dumps({
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
                            "content": message
                        },
                        {
                            "tag": "action",
                            "actions": [
                                {
                                    "tag": "button",
                                    "text": {
                                        "content": "查看详情",
                                        "tag": "plain_text"
                                    },
                                    "type": "danger",  # 紧急按钮样式
                                    "value": {}
                                }
                            ]
                        }
                    ]
                })
            }

        for attempt in range(max_retries):
            try:
                logger.info(f"正在发送紧急消息到飞书 (目标类型: {receive_id_type}, 尝试 {attempt + 1}/{max_retries})")
                response = requests.post(url, headers=headers, json=data, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('code') == 0:
                        logger.info("🚨 紧急消息成功发送到飞书！")
                        return True
                    else:
                        logger.error(f"飞书API返回错误: {result.get('msg')} (code: {result.get('code')})")
                else:
                    logger.error(f"HTTP错误: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"发送飞书消息异常 (尝试 {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
    
    logger.error("❌ 紧急消息发送最终失败")
    return False

def send_error_alert(error_message: str, max_retries: int = MAX_RETRIES):
    """
    发送错误警报到飞书（使用应用认证）
    """
    access_token = get_access_token()
    if not access_token:
        logger.error("❌ 无法获取访问令牌，错误警报发送失败")
        return False

    # 构建错误警报消息
    alert_msg = f"**🚨 机器人故障警报**\n\n**错误详情**：{error_message}\n\n请及时检查机器人状态！\n\n*DeepSeek-V3 监控系统*"

    # 发送错误警报
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=user_id"  # 可以根据需要修改为chat_id
    user_id = os.environ.get('LARK_USER_ID', '')
    data = {
        "receive_id": user_id,
        "content": json.dumps({
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "red",
                "title": {
                    "content": "🚨 机器人故障警报",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"**错误详情**：{error_message}\n\n请及时检查机器人状态！"
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "DeepSeek-V3 监控系统 | 📅 " + time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                    ]
                }
            ]
        }),
        "msg_type": "interactive"
    }

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {access_token}"
    }

    for attempt in range(max_retries):
        try:
            logger.info(f"正在发送错误警报到飞书 (尝试 {attempt + 1}/{max_retries})")
            response = requests.post(url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    logger.info("🚨 错误警报成功发送到飞书！")
                    return True
                else:
                    logger.error(f"飞书API返回错误: {result.get('msg')} (code: {result.get('code')})")
            else:
                logger.error(f"HTTP错误: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"发送飞书错误警报异常 (尝试 {attempt + 1}): {e}")
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
    system_prompt = """你是桥水基金 (Bridgewater) 和高盛 (Goldman Sachs) 联合训练的首席宏观经济分析师。你的服务对象是高净值投资者和跨境贸易商。你的核心能力是穿透新闻表象，直接指出其对资本市场和供应链的深层影响。

# Constraints & Style
1. **严禁废话**：不要说"这则新闻很有趣"、"综上所述"等空话。
2. **极度冷酷**：保持客观、冷静、专业的语调，类似《彭博终端》(Bloomberg Terminal) 或《经济学人》的风格。
3. **数据驱动**：如果新闻中有数字，必须高亮并分析其背后的含义。
4. **拒绝模糊**：不要给模棱两可的建议。如果不确定，指出风险点。
5. **严禁描述图片**：绝对不要在输出中包含 "📸 图片：" 或任何对新闻配图的文字描述。图片由外部系统处理，你只负责文字分析。

# Analysis Framework (必须严格遵守)
请对每条新闻按照以下结构进行输出（Markdown格式）：

### [情绪分 | 1-10] 新闻核心标题 (简练有力，直击痛点)
* **📍 核心事实**：用 1-2 句话概括发生了什么（Who, What, When）。
* **📉 底层逻辑**：为什么这件事重要？（例如：这是政策转向的信号，还是短期噪音？）
* **💰 财富影响 (关键)**：
    * **对跨境电商/贸易**：利好还是利空？（汇率波动、物流成本、关税风险）。
    * **对金融市场**：具体影响哪些资产？（例如：做多黄金、做空美债、关注 A 股光伏板块）如果有少的你也可以自行加上去让他分析的新闻更加专业就可以

---
"""

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