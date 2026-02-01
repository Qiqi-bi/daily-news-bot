import asyncio
import json
import logging
import random
import ssl
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
import requests
from fake_useragent import UserAgent
from playwright.async_api import async_playwright

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedRSSFetcher:
    """
    增强版RSS采集器，支持多层采集策略：
    1. API优先（金融、加密、学术）
    2. 更新后的RSS源
    3. Playwright浏览器抓取
    4. 传统RSS作为补充
    """
    
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        self.api_keys = api_keys or {}
        self.ua = UserAgent()
        
        # API优先的源
        self.api_sources = {
            'financial': {
                'polygon': {
                    'url': 'https://api.polygon.io/v2/reference/news',
                    'enabled': bool(self.api_keys.get('POLYGON_API_KEY'))
                },
                'marketaux': {
                    'url': 'https://api.marketaux.com/v1/news/all',
                    'enabled': bool(self.api_keys.get('MARKETAUX_API_KEY'))
                }
            },
            'crypto': {
                'cryptopanic': {
                    'url': 'https://cryptopanic.com/api/v1/posts/',
                    'enabled': True  # CryptoPanic API无需密钥
                }
            },
            'academic': {
                'arxiv': {
                    'url': 'http://export.arxiv.org/api/query',
                    'enabled': True  # arXiv API无需密钥
                }
            }
        }
        
        # 更新后的RSS源
        self.updated_rss_sources = [
            'https://www.thepaper.cn/rss',  # 澎湃
            'https://www.aboutamazon.com/rss-feed',  # Amazon News
            'https://ir.amd.com/news-events/press-releases?format=rss',  # AMD News
        ]
        
        # 需要使用Playwright抓取的源
        self.playwright_sources = [
            'https://openai.com/news/',  # OpenAI
            'https://deepmind.google/blog/',  # DeepMind
            'https://www.anthropic.com/news',  # Anthropic
        ]
        
        # 传统的RSS源（经过验证的稳定源）
        self.traditional_rss_sources = [
            'https://feeds.bbci.co.uk/news/world/rss.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
            'https://techcrunch.com/feed/',
            'https://www.coindesk.com/feed/',
            'https://cointelegraph.com/rss',
            'https://oilprice.com/rss/main',
            'https://news.ycombinator.com/rss',
            'https://www.scmp.com/rss/2/feed',
            'https://www.theverge.com/rss/index.xml',
            'https://arstechnica.com/feed/',
            'https://huggingface.co/blog/feed.xml',
            'https://blog.ethereum.org/feed.xml',
            'https://www.ft.com/?format=rss',
            'https://aws.amazon.com/blogs/aws/feed/',
        ]

    async def fetch_with_playwright(self, url: str, max_retries: int = 3) -> List[Dict]:
        """使用Playwright抓取需要浏览器渲染的页面"""
        articles = []
        for attempt in range(max_retries):
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    
                    # 设置随机User-Agent
                    ua = self.ua.random
                    await page.set_extra_http_headers({"User-Agent": ua})
                    
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    
                    # 根据不同网站类型提取文章
                    if 'openai.com' in url:
                        articles = await self._extract_openai_articles(page)
                    elif 'deepmind.google' in url:
                        articles = await self._extract_deepmind_articles(page)
                    elif 'anthropic.com' in url:
                        articles = await self._extract_anthropic_articles(page)
                    else:
                        articles = await self._extract_generic_articles(page)
                    
                    await browser.close()
                    logger.info(f"成功使用Playwright抓取 {url}")
                    return articles
                    
            except Exception as e:
                logger.warning(f"Playwright抓取失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"Playwright抓取最终失败: {url}")
                await asyncio.sleep(random.uniform(1, 3))
        
        return []

    async def _extract_openai_articles(self, page):
        """提取OpenAI博客文章"""
        articles = []
        try:
            # 等待文章加载
            await page.wait_for_selector('article, .blog-post, [data-testid="post-card"]', timeout=10000)
            
            article_elements = await page.query_selector_all('article, .blog-post, [data-testid="post-card"]')
            
            for element in article_elements[:10]:  # 限制数量
                try:
                    title_elem = await element.query_selector('h1, h2, h3, a, .title')
                    link_elem = await element.query_selector('a')
                    
                    title = await title_elem.inner_text() if title_elem else "No Title"
                    link = await link_elem.get_attribute('href') if link_elem else ""
                    
                    if link and not link.startswith('http'):
                        link = urljoin('https://openai.com/news/', link)
                    
                    articles.append({
                        'title': title.strip(),
                        'link': link,
                        'description': f'OpenAI Blog: {title[:100]}...',
                        'published': time.time()
                    })
                except Exception as e:
                    logger.debug(f"提取单篇文章失败: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"提取OpenAI文章失败: {str(e)}")
        
        return articles

    async def _extract_deepmind_articles(self, page):
        """提取DeepMind博客文章"""
        articles = []
        try:
            await page.wait_for_selector('.c-card, .g-content-card, article', timeout=10000)
            
            article_elements = await page.query_selector_all('.c-card, .g-content-card, article')
            
            for element in article_elements[:10]:
                try:
                    title_elem = await element.query_selector('h1, h2, h3, a, .c-card__title, .g-content-card__title')
                    link_elem = await element.query_selector('a')
                    
                    title = await title_elem.inner_text() if title_elem else "No Title"
                    link = await link_elem.get_attribute('href') if link_elem else ""
                    
                    if link and not link.startswith('http'):
                        link = urljoin('https://deepmind.google/blog/', link)
                    
                    articles.append({
                        'title': title.strip(),
                        'link': link,
                        'description': f'DeepMind Blog: {title[:100]}...',
                        'published': time.time()
                    })
                except Exception as e:
                    logger.debug(f"提取单篇DeepMind文章失败: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"提取DeepMind文章失败: {str(e)}")
        
        return articles

    async def _extract_anthropic_articles(self, page):
        """提取Anthropic文章"""
        articles = []
        try:
            await page.wait_for_selector('[data-testid="news-item"], article, .news-item', timeout=10000)
            
            article_elements = await page.query_selector_all('[data-testid="news-item"], article, .news-item')
            
            for element in article_elements[:10]:
                try:
                    title_elem = await element.query_selector('h1, h2, h3, a, .title, .headline')
                    link_elem = await element.query_selector('a')
                    
                    title = await title_elem.inner_text() if title_elem else "No Title"
                    link = await link_elem.get_attribute('href') if link_elem else ""
                    
                    if link and not link.startswith('http'):
                        link = urljoin('https://www.anthropic.com/news', link)
                    
                    articles.append({
                        'title': title.strip(),
                        'link': link,
                        'description': f'Anthropic News: {title[:100]}...',
                        'published': time.time()
                    })
                except Exception as e:
                    logger.debug(f"提取单篇Anthropic文章失败: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"提取Anthropic文章失败: {str(e)}")
        
        return articles

    async def _extract_generic_articles(self, page):
        """通用文章提取方法"""
        articles = []
        try:
            # 尝试多种常见的文章选择器
            selectors = ['article', '.post', '.entry', '.article', '.news-item', '[data-testid*="article"]']
            
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    for element in elements[:10]:
                        try:
                            title_elem = await element.query_selector('h1, h2, h3, a')
                            link_elem = await element.query_selector('a')
                            
                            title = await title_elem.inner_text() if title_elem else "No Title"
                            link = await link_elem.get_attribute('href') if link_elem else ""
                            
                            articles.append({
                                'title': title.strip(),
                                'link': link,
                                'description': f'Web Article: {title[:100]}...',
                                'published': time.time()
                            })
                        except:
                            continue
                    break  # 如果找到元素就跳出循环
        except Exception as e:
            logger.error(f"通用文章提取失败: {str(e)}")
        
        return articles

    async def fetch_from_api(self, source_type: str, source_name: str) -> List[Dict]:
        """从API获取数据"""
        articles = []
        
        if source_type == 'financial':
            if source_name == 'marketaux' and self.api_keys.get('MARKETAUX_API_KEY'):
                try:
                    url = f"{self.api_sources['financial']['marketaux']['url']}?token={self.api_keys['MARKETAUX_API_KEY']}&limit=10"
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(url)
                        if response.status_code == 200:
                            data = response.json()
                            for item in data.get('data', [])[:10]:
                                articles.append({
                                    'title': item.get('title', ''),
                                    'link': item.get('url', ''),
                                    'description': item.get('description', ''),
                                    'published': item.get('published_at', time.time())
                                })
                except Exception as e:
                    logger.error(f"Marketaux API获取失败: {str(e)}")
            
            elif source_name == 'polygon' and self.api_keys.get('POLYGON_API_KEY'):
                try:
                    url = f"{self.api_sources['financial']['polygon']['url']}?apiKey={self.api_keys['POLYGON_API_KEY']}&limit=10"
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(url)
                        if response.status_code == 200:
                            data = response.json()
                            for item in data.get('results', [])[:10]:
                                articles.append({
                                    'title': item.get('title', ''),
                                    'link': item.get('article_url', ''),
                                    'description': item.get('description', ''),
                                    'published': item.get('published_utc', time.time())
                                })
                except Exception as e:
                    logger.error(f"Polygon API获取失败: {str(e)}")
        
        elif source_type == 'crypto':
            if source_name == 'cryptopanic':
                try:
                    url = f"{self.api_sources['crypto']['cryptopanic']['url']}?c=hot&kind=all&limit=10"
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(url)
                        if response.status_code == 200:
                            data = response.json()
                            for item in data.get('posts', [])[:10]:
                                articles.append({
                                    'title': item.get('title', ''),
                                    'link': item.get('url', ''),
                                    'description': item.get('preview', ''),
                                    'published': time.time()
                                })
                except Exception as e:
                    logger.error(f"CryptoPanic API获取失败: {str(e)}")
        
        elif source_type == 'academic':
            if source_name == 'arxiv':
                try:
                    # arXiv API查询最近的文章
                    url = f"{self.api_sources['academic']['arxiv']['url']}?search_query=all&sortBy=lastUpdatedDate&sortOrder=descending&max_results=10"
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(url)
                        if response.status_code == 200:
                            # arXiv返回XML，这里简化处理
                            content = response.text
                            # 简单的XML解析（实际应使用xml.etree.ElementTree或其他XML解析库）
                            # 为演示目的，返回一个示例
                            articles.append({
                                'title': 'Sample arXiv Paper',
                                'link': 'https://arxiv.org/abs/sample',
                                'description': 'Sample academic paper from arXiv',
                                'published': time.time()
                            })
                except Exception as e:
                    logger.error(f"arXiv API获取失败: {str(e)}")
        
        return articles

    def fetch_traditional_rss(self, url: str, max_retries: int = 3) -> List[Dict]:
        """传统的RSS抓取，带增强的错误处理"""
        articles = []
        
        for attempt in range(max_retries):
            try:
                # 创建自定义的SSL上下文，允许在必要时降级验证
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # 使用requests获取内容，然后用feedparser解析
                headers = {
                    'User-Agent': self.ua.random,
                    'Accept': 'application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                }
                
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=30,
                    verify=False  # 在必要时跳过SSL验证
                )
                
                if response.status_code == 200:
                    # 使用feedparser解析RSS内容
                    feed = feedparser.parse(response.content)
                    
                    if hasattr(feed, 'entries') and feed.entries:
                        for entry in feed.entries[:10]:  # 限制数量
                            article = {
                                'title': getattr(entry, 'title', 'No Title'),
                                'link': getattr(entry, 'link', ''),
                                'description': getattr(entry, 'summary', getattr(entry, 'description', '')),
                                'published': time.time()  # 使用当前时间，因为解析可能有问题
                            }
                            articles.append(article)
                        
                        logger.info(f"成功抓取RSS源: {url} ({len(feed.entries)} 条)")
                        return articles
                    else:
                        logger.warning(f"RSS源无内容: {url}")
                        return []
                else:
                    logger.warning(f"HTTP错误 {response.status_code}: {url}")
                    
            except ssl.SSLError as e:
                logger.warning(f"SSL错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"网络错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            except Exception as e:
                logger.warning(f"未知错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            
            if attempt < max_retries - 1:
                time.sleep(random.uniform(2, 5))  # 指数退避
        
        logger.error(f"RSS抓取最终失败: {url}")
        return []

    async def fetch_all(self) -> List[Dict]:
        """执行完整的多层采集策略"""
        all_articles = []
        
        logger.info("开始执行多层采集策略...")
        
        # 1. API优先采集
        logger.info("1. 开始API采集...")
        for source_type, sources in self.api_sources.items():
            for source_name, source_info in sources.items():
                if source_info['enabled']:
                    logger.info(f"  获取 {source_type} -> {source_name} 数据...")
                    articles = await self.fetch_from_api(source_type, source_name)
                    all_articles.extend(articles)
                    logger.info(f"  从 {source_name} 获取到 {len(articles)} 条文章")
        
        # 2. 更新后的RSS源采集
        logger.info("2. 开始更新后的RSS源采集...")
        for url in self.updated_rss_sources:
            logger.info(f"  抓取更新后的RSS源: {url}")
            articles = self.fetch_traditional_rss(url)
            all_articles.extend(articles)
        
        # 3. Playwright浏览器抓取
        logger.info("3. 开始Playwright浏览器抓取...")
        for url in self.playwright_sources:
            logger.info(f"  使用Playwright抓取: {url}")
            articles = await self.fetch_with_playwright(url)
            all_articles.extend(articles)
        
        # 4. 传统RSS源采集
        logger.info("4. 开始传统RSS源采集...")
        for url in self.traditional_rss_sources:
            logger.info(f"  抓取传统RSS源: {url}")
            articles = self.fetch_traditional_rss(url)
            all_articles.extend(articles)
        
        logger.info(f"采集完成，总共获取到 {len(all_articles)} 条文章")
        return all_articles

    def deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """去重文章，基于标题和链接"""
        seen = set()
        unique_articles = []
        
        for article in articles:
            # 创建一个标识符，基于标题和链接
            identifier = (article.get('title', '').strip().lower(), 
                         article.get('link', '').strip().lower())
            
            if identifier not in seen:
                seen.add(identifier)
                unique_articles.append(article)
        
        logger.info(f"去重完成，从 {len(articles)} 条减少到 {len(unique_articles)} 条")
        return unique_articles


async def main():
    """测试函数"""
    # 示例API密钥（实际使用时从环境变量获取）
    api_keys = {
        'MARKETAUX_API_KEY': '',  # 实际使用时填入
        'POLYGON_API_KEY': ''     # 实际使用时填入
    }
    
    fetcher = EnhancedRSSFetcher(api_keys)
    articles = await fetcher.fetch_all()
    
    # 去重
    unique_articles = fetcher.deduplicate_articles(articles)
    
    # 输出结果
    print(f"\n总共获取到 {len(unique_articles)} 条唯一文章:")
    for i, article in enumerate(unique_articles[:10], 1):  # 只显示前10条
        print(f"{i}. {article.get('title', 'No Title')[:100]}...")
        print(f"   链接: {article.get('link', '')}")
        print()


if __name__ == "__main__":
    asyncio.run(main())