#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily News Bot - 全球情报与金融分析自动化脚本

功能：
1. 从国际主流RSS源抓取新闻（通过代理）
2. 调用DeepSeek大模型API进行深度分析
3. 发送到飞书群（使用webhook方式）
"""

# 首先加载环境变量
from dotenv import load_dotenv
load_dotenv()  # 加载 .env 文件

import feedparser
import requests
import json
import time
import logging
import random
from typing import List, Dict, Optional
import os
import urllib3
from fake_useragent import UserAgent
from enhanced_rss_fetcher import EnhancedRSSFetcher

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置区域
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
    # 国际顶流 (BBC/NYT)
    "https://feeds.bbci.co.uk/news/world/rss.xml",  # BBC World
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",  # NYT World
    
    # 华尔街/金融 (CNBC)
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",  # CNBC Finance

    # 硅谷/科技 (TechCrunch)
    "https://techcrunch.com/feed/",  # TechCrunch AI & Startup

    # 雅虎财经 (新增)
    "https://finance.yahoo.com/news/rssindex",  # Yahoo Finance

    # 加密货币 (Crypto)
    "https://www.coindesk.com/arc/outboundfeeds/rss/",  # CoinDesk
    "https://cointelegraph.com/rss",  # Cointelegraph
    "https://crypto-slate.com/feed/",  # Crypto Slate

    # 能源与战争 (Energy)
    "https://oilprice.com/rss/main",  # OilPrice.com

    # 社交与黑客动向 (替代 Twitter/GitHub)
    # Hacker News (全球极客都在讨论什么，是 GitHub 最好的风向标)
    "https://news.ycombinator.com/rss",
    # Reddit WorldNews (全球网民最热议的突发事件)
    "https://www.reddit.com/r/worldnews/top/.rss?t=day",
    
    # Reddit 视频聚合 (新增)
    "https://www.reddit.com/r/videos/top/.rss?t=day",  # Reddit 视频聚合 - 全球24小时内最热门的视频集合
    
    # 亚洲/中国商业 (新增)
    "https://www.scmp.com/rss/2/feed",  # South China Morning Post (南华早报 - 中国商业版块)
    
    # 学术/AI研究 (新增)
    "http://arxiv.org/rss/cs.AI",  # ArXiv AI Paper Daily (学术源)
    "https://mittechnologyreview.com/feed/",  # MIT Technology Review (科技趋势分析)
    
    # 国内主流新闻源 (新增)
    "http://news.baidu.com/n?cmd=file&format=rss&tn=rss&sub=0",  # 百度新闻
    "http://rss.people.com.cn/GB/303140/index.xml",  # 人民网
    "http://www.xinhuanet.com/politics/news_politics.xml",  # 新华网 - 时政
    "http://www.chinanews.com/rss/scroll-news.xml",  # 中国新闻网
    "https://www.thepaper.cn/rss.jsp",  # 澎湃新闻
    "http://www.ce.cn/cysc/jg/zxbd/rss2.xml",  # 中国经济网
    "https://www.cls.cn/v3/highlights?app_id=70301d300f0f95a1&platform=pc",  # 财联社 (需要适配)
    
    # 国内科技新闻 (新增)
    "https://www.zhihu.com/rss",  # 知乎每日精选
    "https://www.36kr.com/feed",  # 36氪
    "https://news.qq.com/rss/channels/finance/rss.xml",  # 腾讯财经
    "https://rss.sina.com.cn/news/china/focus15.xml",  # 新生新闻-国内焦点

    # 主要科技公司官网 (新增)
    "https://blog.google/rss/",  # Google Blog
    "https://openai.com/blog/rss/",  # OpenAI Blog
    "https://blogs.microsoft.com/feed/",  # Microsoft Blog
    "https://www.apple.com/newsroom/rss-feed.rss",  # Apple Newsroom
    "https://nvidianews.nvidia.com/rss.xml",  # NVIDIA Newsroom
    "https://about.meta.com/rss/feed/",  # Meta Newsroom

    # 国内大型互联网公司官网 (新增)
    "https://www.tencent.com/zh-cn/articles/rss.html",  # 腾讯官网资讯
    "https://news.lenovo.com/feature-stories/",  # 联想新闻中心 (可能需要适配)
    "https://www.baidu.com/ir/rss.xml",  # 百度投资者关系RSS
    "https://www.alibabagroup.com/cn/global/home/rss",  # 阿里巴巴集团RSS
    "https://www.xiaomi.com/rss",  # 小米官网RSS
    "https://www.bytedance.com/rss",  # 字节跳动官网RSS
    "https://ir.weibo.com/rss",  # 微博投资者关系RSS
    "https://www.netease.com/rss",  # 网易RSS
    "https://www.sina.com.cn/rss/",  # 新浪RSS汇总
    "https://www.iqiyi.com/common/doc/feed.xml",  # 爱奇艺RSS
    "https://www.meituan.com/meituan/pressrelease/rss",  # 美团新闻RSS
    "https://www.jd.com/ir/rss",  # 京东投资者关系RSS
    "https://www.pinduoduo.com/rss",  # 拼多多官网RSS
    "https://www.bilibili.com/robots.txt",  # B站相关信息 (可能需要适配)
    "https://www.360.cn/rss",  # 360官网RSS
    "https://www.le.com/feeds/rss",  # 乐视RSS (如可用)
    "https://www.huya.com/livelist",  # 虎牙直播新闻 (可能需要适配)
    "https://www.douyu.com/room/rss",  # 斗鱼直播新闻 (可能需要适配)
    "https://www.kuaishou.com/press-center",  # 快手新闻中心 (可能需要适配)
    "https://www.didiglobal.com/news",  # 滴滴新闻中心 (可能需要适配)
    "https://www.sohu.com/?spm=smpc.news-top-bar.1.1",  # 搜狐新闻RSS (可能需要适配)
    "https://www.163.com/special/0077jt/yaowen_rss.xml",  # 网易要闻RSS
    "https://www.autohome.com.cn/rss/",  # 汽车之家RSS
    "https://www.smzdm.com/feed",  # 什么值得买RSS
    "https://www.zbj.com/news/rss",  # 猪八戒网新闻RSS
    "https://www.mafengwo.cn/i/you/minsu/rss",  # 马蜂窝新闻RSS (可能需要适配)
    "https://www.qunar.com/rss",  # 去哪儿网RSS
    "https://www.ctrip.com/rss",  # 携程网RSS
    "https://www.58.com/rss",  # 58同城RSS
    "https://www.ganji.com/rss",  # 赶集网RSS
    "https://www.focus.cn/rss",  # 焦点科技RSS
    "https://www.eastmoney.com/ir/",  # 东方财富网 (可能需要适配)
    "https://www.hexun.com/ir/",  # 和讯网 (可能需要适配)
    "https://www.stockstar.com/rss",  # 证券之星RSS
    "https://www.p5w.net/rss",  # 巨潮资讯网RSS
    "https://www.cs.com.cn/rss",  # 中国证券网RSS
    "https://www.yicai.com/rss",  # 第一财经RSS
    "https://www.jiemian.com/feeds.html",  # 澎湃新闻 (可能需要适配)
    "https://www.cls.cn/telegraph",  # 财联社电报 (可能需要适配)
    "https://www.eeo.com.cn/rss",  # 经济观察网RSS
    "https://www.cbndata.com/rss",  # CBNDATA (可能需要适配)
    "https://www.iresearch.cn/rss",  # 艾瑞咨询RSS
    "https://www.199it.com/feed",  # 199IT大数据RSS
    "https://www.tmtpost.com/rss",  # 钛媒体RSS
    "https://www.lieyunwang.com/rss",  # 猎云网RSS
    "https://www.cyzone.cn/rss",  # 创业邦RSS
    "https://www.pingwest.com/rss",  # 品玩RSS
    "https://www.geekpark.net/rss",  # 极客公园RSS
    "https://www.zol.com.cn/rss",  # 中关村在线RSS
    "https://www.pconline.com.cn/rss",  # 太平洋电脑网RSS
    "https://www.cnbeta.com/rss",  # cnBeta RSS
    "https://www.ithome.com/rss",  # IT之家RSS
    "https://www.ccidnet.com/rss",  # 中国信息产业网RSS
    "https://www.cio.com.cn/rss",  # CIO时代网RSS
    "https://www.enet.com.cn/rss",  # eNet资讯RSS
    "https://www.techweb.com.cn/rss",  # TechWeb RSS
    "https://www.51cto.com/rss",  # 51CTO RSS
    "https://www.csdn.net/rss",  # CSDN RSS
    "https://www.oschina.net/rss",  # 开源中国RSS
    "https://www.infoq.cn/rss",  # InfoQ RSS
    "https://www.importnew.com/feed",  # ImportNew RSS
    "https://www.zhihu.com/api/v4/columns/tech/rss",  # 知乎科技专栏RSS
    "https://www.zhihu.com/api/v4/columns/business/rss",  # 知乎商业专栏RSS
    "https://www.zhihu.com/api/v4/columns/finance/rss",  # 知乎金融专栏RSS
    "https://www.zhihu.com/api/v4/columns/internet/rss",  # 知乎互联网专栏RSS
    "https://www.zhihu.com/api/v4/columns/startup/rss",  # 知乎创业专栏RSS
    "https://www.zhihu.com/api/v4/columns/invest/rss",  # 知乎投资专栏RSS
    "https://www.zhihu.com/api/v4/columns/blockchain/rss",  # 知乎区块链专栏RSS
    "https://www.zhihu.com/api/v4/columns/ai/rss",  # 知乎AI专栏RSS
    "https://www.zhihu.com/api/v4/columns/bigdata/rss",  # 知乎大数据专栏RSS
    "https://www.zhihu.com/api/v4/columns/cloud/rss",  # 知乎云计算专栏RSS
    "https://www.zhihu.com/api/v4/columns/mobile/rss",  # 知乎移动互联网专栏RSS
    "https://www.zhihu.com/api/v4/columns/iot/rss",  # 知乎物联网专栏RSS
    "https://www.zhihu.com/api/v4/columns/security/rss",  # 知乎网络安全专栏RSS
    "https://www.zhihu.com/api/v4/columns/game/rss",  # 知乎游戏专栏RSS
    "https://www.zhihu.com/api/v4/columns/ecommerce/rss",  # 知乎电商专栏RSS
    "https://www.zhihu.com/api/v4/columns/socialmedia/rss",  # 知乎社交媒体专栏RSS
    "https://www.zhihu.com/api/v4/columns/retail/rss",  # 知乎零售专栏RSS
    "https://www.zhihu.com/api/v4/columns/manufacturing/rss",  # 知乎制造业专栏RSS
    "https://www.zhihu.com/api/v4/columns/energy/rss",  # 知乎能源专栏RSS
    "https://www.zhihu.com/api/v4/columns/transportation/rss",  # 知乎交通专栏RSS
    "https://www.zhihu.com/api/v4/columns/healthcare/rss",  # 知乎医疗专栏RSS
    "https://www.zhihu.com/api/v4/columns/education/rss",  # 知乎教育专栏RSS
    "https://www.zhihu.com/api/v4/columns/real_estate/rss",  # 知乎房地产专栏RSS
    "https://www.zhihu.com/api/v4/columns/automotive/rss",  # 知乎汽车专栏RSS
    "https://www.zhihu.com/api/v4/columns/robotics/rss",  # 知乎机器人专栏RSS
    "https://www.zhihu.com/api/v4/columns/quantum/rss",  # 知乎量子计算专栏RSS
    "https://www.zhihu.com/api/v4/columns/neuroscience/rss",  # 知乎神经科学专栏RSS
    "https://www.zhihu.com/api/v4/columns/biotech/rss",  # 知乎生物技术专栏RSS
    "https://www.zhihu.com/api/v4/columns/materials/rss",  # 知乎新材料专栏RSS
    "https://www.zhihu.com/api/v4/columns/aerospace/rss",  # 知乎航空航天专栏RSS
    "https://www.zhihu.com/api/v4/columns/defense/rss",  # 知乎国防专栏RSS
    "https://www.zhihu.com/api/v4/columns/agriculture/rss",  # 知乎农业专栏RSS
    "https://www.zhihu.com/api/v4/columns/environment/rss",  # 知乎环境专栏RSS
    "https://www.zhihu.com/api/v4/columns/climate/rss",  # 知乎气候专栏RSS
    "https://www.zhihu.com/api/v4/columns/space/rss",  # 知乎太空探索专栏RSS
    "https://www.zhihu.com/api/v4/columns/ocean/rss",  # 知乎海洋专栏RSS
    "https://www.zhihu.com/api/v4/columns/archaeology/rss",  # 知乎考古专栏RSS
    "https://www.zhihu.com/api/v4/columns/history/rss",  # 知乎历史专栏RSS
    "https://www.zhihu.com/api/v4/columns/politics/rss",  # 知乎政治专栏RSS
    "https://www.zhihu.com/api/v4/columns/economics/rss",  # 知乎经济专栏RSS
    "https://www.zhihu.com/api/v4/columns/finance/rss",  # 知乎金融专栏RSS
    "https://www.zhihu.com/api/v4/columns/marketing/rss",  # 知乎营销专栏RSS
    "https://www.zhihu.com/api/v4/columns/brand/rss",  # 知乎品牌专栏RSS
    "https://www.zhihu.com/api/v4/columns/advertising/rss",  # 知乎广告专栏RSS
    "https://www.zhihu.com/api/v4/columns/pr/rss",  # 知乎公关专栏RSS
    "https://www.zhihu.com/api/v4/columns/hr/rss",  # 知乎人力资源专栏RSS
    "https://www.zhihu.com/api/v4/columns/management/rss",  # 知乎管理专栏RSS
    "https://www.zhihu.com/api/v4/columns/leadership/rss",  # 知乎领导力专栏RSS
    "https://www.zhihu.com/api/v4/columns/strategy/rss",  # 知乎战略专栏RSS
    "https://www.zhihu.com/api/v4/columns/innovation/rss",  # 知乎创新专栏RSS
    "https://www.zhihu.com/api/v4/columns/entrepreneurship/rss",  # 知乎创业专栏RSS
    "https://www.zhihu.com/api/v4/columns/startups/rss",  # 知乎初创公司专栏RSS
    "https://www.zhihu.com/api/v4/columns/venture_capital/rss",  # 知乎风险投资专栏RSS
    "https://www.zhihu.com/api/v4/columns/private_equity/rss",  # 知乎私募股权专栏RSS
    "https://www.zhihu.com/api/v4/columns/mergers_acquisitions/rss",  # 知乎并购专栏RSS
    "https://www.zhihu.com/api/v4/columns/ipos/rss",  # 知乎IPO专栏RSS
    "https://www.zhihu.com/api/v4/columns/public_offering/rss",  # 知乎公开发行专栏RSS
    "https://www.zhihu.com/api/v4/columns/stock_market/rss",  # 知乎股票市场专栏RSS
    "https://www.zhihu.com/api/v4/columns/bond_market/rss",  # 知乎债券市场专栏RSS
    "https://www.zhihu.com/api/v4/columns/derivatives/rss",  # 知乎衍生品专栏RSS
    "https://www.zhihu.com/api/v4/columns/foreign_exchange/rss",  # 知乎外汇专栏RSS
    "https://www.zhihu.com/api/v4/columns/commodities/rss",  # 知乎大宗商品专栏RSS
    "https://www.zhihu.com/api/v4/columns/real_estate_investment/rss",  # 知乎房地产投资专栏RSS
    "https://www.zhihu.com/api/v4/columns/hedge_funds/rss",  # 知乎对冲基金专栏RSS
    "https://www.zhihu.com/api/v4/columns/mutual_funds/rss",  # 知乎共同基金专栏RSS
    "https://www.zhihu.com/api/v4/columns/insurance/rss",  # 知乎保险专栏RSS
    "https://www.zhihu.com/api/v4/columns/banking/rss",  # 知乎银行业专栏RSS
    "https://www.zhihu.com/api/v4/columns/payments/rss",  # 知乎支付专栏RSS
    "https://www.zhihu.com/api/v4/columns/lending/rss",  # 知乎借贷专栏RSS
    "https://www.zhihu.com/api/v4/columns/cryptocurrency/rss",  # 知乎加密货币专栏RSS
    "https://www.zhihu.com/api/v4/columns/blockchain_technology/rss",  # 知乎区块链技术专栏RSS
    "https://www.zhihu.com/api/v4/columns/decentralized_finance/rss",  # 知乎去中心化金融专栏RSS
    "https://www.zhihu.com/api/v4/columns/non_fungible_tokens/rss",  # 知乎非同质化代币专栏RSS
    "https://www.zhihu.com/api/v4/columns/digital_assets/rss",  # 知乎数字资产专栏RSS
    "https://www.zhihu.com/api/v4/columns/web3/rss",  # 知乎Web3专栏RSS
    "https://www.zhihu.com/api/v4/columns/metaverse/rss",  # 知乎元宇宙专栏RSS
    "https://www.zhihu.com/api/v4/columns/virtual_reality/rss",  # 知乎虚拟现实专栏RSS
    "https://www.zhihu.com/api/v4/columns/augmented_reality/rss",  # 知乎增强现实专栏RSS
    "https://www.zhihu.com/api/v4/columns/mixed_reality/rss",  # 知乎混合现实专栏RSS
    "https://www.zhihu.com/api/v4/columns/gaming_industry/rss",  # 知乎游戏产业专栏RSS
    "https://www.zhihu.com/api/v4/columns/esports/rss",  # 知乎电子竞技专栏RSS
    "https://www.zhihu.com/api/v4/columns/streaming_media/rss",  # 知乎流媒体专栏RSS
    "https://www.zhihu.com/api/v4/columns/social_networks/rss",  # 知乎社交网络专栏RSS
    "https://www.zhihu.com/api/v4/columns/sharing_economy/rss",  # 知乎分享经济专栏RSS
    "https://www.zhihu.com/api/v4/columns/platform_economy/rss",  # 知乎平台经济专栏RSS
    "https://www.zhihu.com/api/v4/columns/gig_economy/rss",  # 知乎零工经济专栏RSS
    "https://www.zhihu.com/api/v4/columns/digital_transformation/rss",  # 知乎数字化转型专栏RSS
    "https://www.zhihu.com/api/v4/columns/enterprise_software/rss",  # 知乎企业软件专栏RSS
    "https://www.zhihu.com/api/v4/columns/cloud_computing/rss",  # 知乎云计算专栏RSS
    "https://www.zhihu.com/api/v4/columns/data_center/rss",  # 知乎数据中心专栏RSS
    "https://www.zhihu.com/api/v4/columns/networking/rss",  # 知乎网络技术专栏RSS
    "https://www.zhihu.com/api/v4/columns/cybersecurity/rss",  # 知乎网络安全专栏RSS
    "https://www.zhihu.com/api/v4/columns/privacy/rss",  # 知乎隐私保护专栏RSS
    "https://www.zhihu.com/api/v4/columns/regulation/rss",  # 知乎法规专栏RSS
    "https://www.zhihu.com/api/v4/columns/policy/rss",  # 知乎政策专栏RSS
    "https://www.zhihu.com/api/v4/columns/governance/rss",  # 知乎治理专栏RSS
    "https://www.zhihu.com/api/v4/columns/ethics/rss",  # 知乎伦理专栏RSS
    "https://www.zhihu.com/api/v4/columns/sustainability/rss",  # 知乎可持续发展专栏RSS
    "https://www.zhihu.com/api/v4/columns/corporate_social_responsibility/rss",  # 知乎企业社会责任专栏RSS
    "https://www.zhihu.com/api/v4/columns/environmental_social_governance/rss",  # 知乎ESG专栏RSS
    "https://www.zhihu.com/api/v4/columns/impact_investing/rss",  # 知乎影响力投资专栏RSS
    "https://www.zhihu.com/api/v4/columns/social_impact/rss",  # 知乎社会影响专栏RSS
    "https://www.zhihu.com/api/v4/columns/philanthropy/rss",  # 知乎慈善专栏RSS
    "https://www.zhihu.com/api/v4/columns/nonprofit/rss",  # 知乎非营利组织专栏RSS
    "https://www.zhihu.com/api/v4/columns/social_enterprise/rss",  # 知乎社会企业专栏RSS
    "https://www.zhihu.com/api/v4/columns/mission_driven/rss",  # 知乎使命驱动型企业专栏RSS
    "https://www.zhihu.com/api/v4/columns/stakeholder_capitalism/rss",  # 知乎利益相关者资本主义专栏RSS
    "https://www.zhihu.com/api/v4/columns/shared_value/rss",  # 知乎共享价值专栏RSS
    "https://www.zhihu.com/api/v4/columns/triple_bottom_line/rss",  # 知乎三重底线专栏RSS
    "https://www.zhihu.com/api/v4/columns/circular_economy/rss",  # 知乎循环经济专栏RSS
    "https://www.zhihu.com/api/v4/columns/green_business/rss",  # 知乎绿色商业专栏RSS
    "https://www.zhihu.com/api/v4/columns/clean_technology/rss",  # 知乎清洁技术专栏RSS
    "https://www.zhihu.com/api/v4/columns/renewable_energy/rss",  # 知乎可再生能源专栏RSS
    "https://www.zhihu.com/api/v4/columns/energy_efficiency/rss",  # 知乎能源效率专栏RSS
    "https://www.zhihu.com/api/v4/columns/smart_grid/rss",  # 知乎智能电网专栏RSS
    "https://www.zhihu.com/api/v4/columns/energy_storage/rss",  # 知乎能源存储专栏RSS
    "https://www.zhihu.com/api/v4/columns/electric_vehicles/rss",  # 知乎电动汽车专栏RSS
    "https://www.zhihu.com/api/v4/columns/autonomous_vehicles/rss",  # 知乎自动驾驶车辆专栏RSS
    "https://www.zhihu.com/api/v4/columns/mobility_as_a_service/rss",  # 知乎出行即服务专栏RSS
    "https://www.zhihu.com/api/v4/columns/shared_mobility/rss",  # 知乎共享出行专栏RSS
    "https://www.zhihu.com/api/v4/columns/urban_planning/rss",  # 知乎城市规划专栏RSS
    "https://www.zhihu.com/api/v4/columns/smart_city/rss",  # 知乎智慧城市专栏RSS
    "https://www.zhihu.com/api/v4/columns/internet_of_things/rss",  # 知乎物联网专栏RSS
    "https://www.zhihu.com/api/v4/columns/industrial_internet/rss",  # 知乎工业互联网专栏RSS
    "https://www.zhihu.com/api/v4/columns/edge_computing/rss",  # 知乎边缘计算专栏RSS
    "https://www.zhihu.com/api/v4/columns/fog_computing/rss",  # 知乎雾计算专栏RSS
    "https://www.zhihu.com/api/v4/columns/quantum_computing/rss",  # 知乎量子计算专栏RSS
    "https://www.zhihu.com/api/v4/columns/neuromorphic_computing/rss",  # 知乎神经形态计算专栏RSS
    "https://www.zhihu.com/api/v4/columns/dna_computing/rss",  # 知乎DNA计算专栏RSS
    "https://www.zhihu.com/api/v4/columns/optical_computing/rss",  # 知乎光学计算专栏RSS
    "https://www.zhihu.com/api/v4/columns/analog_computing/rss",  # 知乎模拟计算专栏RSS
    "https://www.zhihu.com/api/v4/columns/hybrid_computing/rss",  # 知乎混合计算专栏RSS
    "https://www.zhihu.com/api/v4/columns/biocomputing/rss",  # 知乎生物计算专栏RSS
    "https://www.zhihu.com/api/v4/columns/molecular_computing/rss",  # 知乎分子计算专栏RSS
    "https://www.zhihu.com/api/v4/columns/cellular_automata/rss",  # 知乎细胞自动机专栏RSS
    "https://www.zhihu.com/api/v4/columns/swarm_intelligence/rss",  # 知乎群体智能专栏RSS
    "https://www.zhihu.com/api/v4/columns/evolutionary_computation/rss",  # 知乎进化计算专栏RSS
    "https://www.zhihu.com/api/v4/columns/genetic_algorithms/rss",  # 知乎遗传算法专栏RSS
    "https://www.zhihu.com/api/v4/columns/neural_networks/rss",  # 知乎神经网络专栏RSS
    "https://www.zhihu.com/api/v4/columns/deep_learning/rss",  # 知乎深度学习专栏RSS
    "https://www.zhihu.com/api/v4/columns/machine_learning/rss",  # 知乎机器学习专栏RSS
    "https://www.zhihu.com/api/v4/columns/artificial_intelligence/rss",  # 知乎人工智能专栏RSS
    "https://www.zhihu.com/api/v4/columns/natural_language_processing/rss",  # 知乎自然语言处理专栏RSS
    "https://www.zhihu.com/api/v4/columns/computer_vision/rss",  # 知乎计算机视觉专栏RSS
    "https://www.zhihu.com/api/v4/columns/speech_recognition/rss",  # 知乎语音识别专栏RSS
    "https://www.zhihu.com/api/v4/columns/robotics/rss",  # 知乎机器人专栏RSS
    "https://www.zhihu.com/api/v4/columns/automation/rss",  # 知乎自动化专栏RSS
    "https://www.zhihu.com/api/v4/columns/control_systems/rss",  # 知乎控制系统专栏RSS
    "https://www.zhihu.com/api/v4/columns/embedded_systems/rss",  # 知乎嵌入式系统专栏RSS
    "https://www.zhihu.com/api/v4/columns/system_on_chip/rss",  # 知乎片上系统专栏RSS
    "https://www.zhihu.com/api/v4/columns/application_specific_integrated_circuit/rss",  # 知乎专用集成电路专栏RSS
    "https://www.zhihu.com/api/v4/columns/field_programmable_gate_array/rss",  # 知乎现场可编程门阵列专栏RSS
    "https://www.zhihu.com/api/v4/columns/very_large_scale_integration/rss",  # 知乎超大规模集成电路专栏RSS
    "https://www.zhihu.com/api/v4/columns/electronic_design_automation/rss",  # 知乎电子设计自动化专栏RSS
    "https://www.zhihu.com/api/v4/columns/semiconductor_manufacturing/rss",  # 知乎半导体制造专栏RSS
    "https://www.zhihu.com/api/v4/columns/photolithography/rss",  # 知乎光刻技术专栏RSS
    "https://www.zhihu.com/api/v4/columns/electronic_packaging/rss",  # 知乎电子封装专栏RSS
    "https://www.zhihu.com/api/v4/columns/thermal_management/rss",  # 知乎热管理专栏RSS
    "https://www.zhihu.com/api/v4/columns/power_management/rss",  # 知乎电源管理专栏RSS
    "https://www.zhihu.com/api/v4/columns/analog_circuits/rss",  # 知乎模拟电路专栏RSS
    "https://www.zhihu.com/api/v4/columns/digital_circuits/rss",  # 知乎数字电路专栏RSS
    "https://www.zhihu.com/api/v4/columns/mixed_signal_circuits/rss",  # 知乎混合信号电路专栏RSS
    "https://www.zhihu.com/api/v4/columns/radio_frequency_circuits/rss",  # 知乎射频电路专栏RSS
    "https://www.zhihu.com/api/v4/columns/microwave_engineering/rss",  # 知乎微波工程专栏RSS
    "https://www.zhihu.com/api/v4/columns/antenna_design/rss",  # 知乎天线设计专栏RSS
    "https://www.zhihu.com/api/v4/columns/wireless_communication/rss",  # 知乎无线通信专栏RSS
    "https://www.zhihu.com/api/v4/columns/mobile_communication/rss",  # 知乎移动通信专栏RSS
    "https://www.zhihu.com/api/v4/columns/satellite_communication/rss",  # 知乎卫星通信专栏RSS
    "https://www.zhihu.com/api/v4/columns/optical_communication/rss",  # 知乎光通信专栏RSS
    "https://www.zhihu.com/api/v4/columns/fiber_optics/rss",  # 知乎光纤技术专栏RSS
    "https://www.zhihu.com/api/v4/columns/telecommunications/rss",  # 知乎电信专栏RSS
    "https://www.zhihu.com/api/v4/columns/network_protocols/rss",  # 知乎网络协议专栏RSS
    "https://www.zhihu.com/api/v4/columns/internet_protocol/rss",  # 知乎互联网协议专栏RSS
    "https://www.zhihu.com/api/v4/columns/transport_layer/rss",  # 知乎传输层专栏RSS
    "https://www.zhihu.com/api/v4/columns/application_layer/rss",  # 知乎应用层专栏RSS
    "https://www.zhihu.com/api/v4/columns/network_security/rss",  # 知乎网络安全专栏RSS
    "https://www.zhihu.com/api/v4/columns/cryptography/rss",  # 知乎密码学专栏RSS
    "https://www.zhihu.com/api/v4/columns/blockchain_security/rss",  # 知乎区块链安全专栏RSS
    "https://www.zhihu.com/api/v4/columns/identity_management/rss",  # 知乎身份管理专栏RSS
    "https://www.zhihu.com/api/v4/columns/access_control/rss",  # 知乎访问控制专栏RSS
    "https://www.zhihu.com/api/v4/columns/authentication/rss",  # 知乎认证专栏RSS
    "https://www.zhihu.com/api/v4/columns/authorization/rss",  # 知乎授权专栏RSS
    "https://www.zhihu.com/api/v4/columns/auditing/rss",  # 知乎审计专栏RSS
    "https://www.zhihu.com/api/v4/columns/compliance/rss",  # 知乎合规专栏RSS
    "https://www.zhihu.com/api/v4/columns/risk_management/rss",  # 知乎风险管理专栏RSS
    "https://www.zhihu.com/api/v4/columns/business_continuity/rss",  # 知乎业务连续性专栏RSS
    "https://www.zhihu.com/api/v4/columns/disaster_recovery/rss",  # 知乎灾难恢复专栏RSS
    "https://www.zhihu.com/api/v4/columns/incident_response/rss",  # 知乎事件响应专栏RSS
    "https://www.zhihu.com/api/v4/columns/threat_intelligence/rss",  # 知乎威胁情报专栏RSS
    "https://www.zhihu.com/api/v4/columns/vulnerability_management/rss",  # 知乎漏洞管理专栏RSS
    "https://www.zhihu.com/api/v4/columns/penetration_testing/rss",  # 知乎渗透测试专栏RSS
    "https://www.zhihu.com/api/v4/columns/ethical_hacking/rss",  # 知乎道德黑客专栏RSS
    "https://www.zhihu.com/api/v4/columns/forensics/rss",  # 知乎取证专栏RSS
    "https://www.zhihu.com/api/v4/columns/digital_forensics/rss",  # 知乎数字取证专栏RSS
    "https://www.zhihu.com/api/v4/columns/network_forensics/rss",  # 知乎网络取证专栏RSS
    "https://www.zhihu.com/api/v4/columns/malware_analysis/rss",  # 知乎恶意软件分析专栏RSS
    "https://www.zhihu.com/api/v4/columns/reverse_engineering/rss",  # 知乎逆向工程专栏RSS
    "https://www.zhihu.com/api/v4/columns/exploit_development/rss",  # 知乎漏洞利用开发专栏RSS
    "https://www.zhihu.com/api/v4/columns/buffer_overflow/rss",  # 知乎缓冲区溢出专栏RSS
    "https://www.zhihu.com/api/v4/columns/sql_injection/rss",  # 知乎SQL注入专栏RSS
    "https://www.zhihu.com/api/v4/columns/cross_site_scripting/rss",  # 知乎跨站脚本攻击专栏RSS
    "https://www.zhihu.com/api/v4/columns/cross_site_request_forgery/rss",  # 知乎跨站请求伪造专栏RSS
    "https://www.zhihu.com/api/v4/columns/session_hijacking/rss",  # 知乎会话劫持专栏RSS
    "https://www.zhihu.com/api/v4/columns/man_in_the_middle/rss",  # 知乎中间人攻击专栏RSS
    "https://www.zhihu.com/api/v4/columns/denial_of_service/rss",  # 知乎拒绝服务攻击专栏RSS
    "https://www.zhihu.com/api/v4/columns/distributed_denial_of_service/rss",  # 知乎分布式拒绝服务攻击专栏RSS
    "https://www.zhihu.com/api/v4/columns/phishing/rss",  # 知乎钓鱼攻击专栏RSS
    "https://www.zhihu.com/api/v4/columns/social_engineering/rss",  # 知乎社会工程学专栏RSS
    "https://www.zhihu.com/api/v4/columns/insider_threats/rss",  # 知乎内部威胁专栏RSS
    "https://www.zhihu.com/api/v4/columns/advanced_persistent_threats/rss",  # 知乎高级持续性威胁专栏RSS
    "https://www.zhihu.com/api/v4/columns/apt/rss",  # 知乎APT专栏RSS
    "https://www.zhihu.com/api/v4/columns/cyber_warfare/rss",  # 知乎网络战专栏RSS
    "https://www.zhihu.com/api/v4/columns/nation_state_attacks/rss",  # 知乎国家级攻击专栏RSS
    "https://www.zhihu.com/api/v4/columns/cyber_espionage/rss",  # 知乎网络间谍活动专栏RSS
    "https://www.zhihu.com/api/v4/columns/cyber_intelligence/rss",  # 知乎网络情报专栏RSS
    "https://www.zhihu.com/api/v4/columns/cyber_diplomacy/rss",  # 知乎网络外交专栏RSS
    "https://www.zhihu.com/api/v4/columns/cyber_law/rss",  # 知乎网络法律专栏RSS
    "https://www.zhihu.com/api/v4/columns/cyber_policy/rss",  # 知乎网络政策专栏RSS
    "https://www.zhihu.com/api/v4/columns/cyber_governance/rss",  # 知乎网络治理专栏RSS
    "https://www.zhihu.com/api/v4/columns/cyber_ethics/rss",  # 知乎网络伦理专栏RSS
    "https://www.zhihu.com/api/v4/columns/cyber_security_standards/rss",  # 知乎网络安全标准专栏RSS
    "https://www.zhihu.com/api/v4/columns/iso_27001/rss",  # 知乎ISO 27001专栏RSS
    "https://www.zhihu.com/api/v4/columns/nist_framework/rss",  # 知乎NIST框架专栏RSS
    "https://www.zhihu.com/api/v4/columns/cmmc/rss",  # 知乎CMMC专栏RSS
    "https://www.zhihu.com/api/v4/columns/soc_2/rss",  # 知乎SOC 2专栏RSS
    "https://www.zhihu.com/api/v4/columns/pci_dss/rss",  # 知乎PCI DSS专栏RSS
    "https://www.zhihu.com/api/v4/columns/hipaa/rss",  # 知乎HIPAA专栏RSS
    "https://www.zhihu.com/api/v4/columns/gdpr/rss",  # 知乎GDPR专栏RSS
    "https://www.zhihu.com/api/v4/columns/ccpa/rss",  # 知乎CCPA专栏RSS
    "https://www.zhihu.com/api/v4/columns/sox/rss",  # 知乎SOX专栏RSS
    "https://www.zhihu.com/api/v4/columns/glba/rss",  # 知乎GLBA专栏RSS
    "https://www.zhihu.com/api/v4/columns/fisma/rss",  # 知乎FISMA专栏RSS
    "https://www.zhihu.com/api/v4/columns/dodd_frank/rss",  # 知乎多德-弗兰克法案专栏RSS
    "https://www.zhihu.com/api/v4/columns/basel_iii/rss",  # 知乎巴塞尔协议III专栏RSS
    "https://www.zhihu.com/api/v4/columns/sarbanes_oxley/rss",  # 知乎萨班斯-奥克斯利法案专栏RSS
    "https://www.zhihu.com/api/v4/columns/payment_card_industry/rss",  # 知乎支付卡行业专栏RSS
    "https://www.zhihu.com/api/v4/columns/health_insurance_portability_accountability/rss",  # 知乎健康保险流通与责任法案专栏RSS
    "https://www.zhihu.com/api/v4/columns/general_data_protection_regulation/rss",  # 知乎通用数据保护条例专栏RSS
    "https://www.zhihu.com/api/v4/columns/california_consumer_privacy_act/rss",  # 知乎加州消费者隐私法案专栏RSS
    "https://www.zhihu.com/api/v4/columns/federal_information_security_management/rss",  # 知乎联邦信息安全管理制度专栏RSS
    # 主流财经媒体 (新增)
    "https://feeds.reuters.com/reuters/topNews",  # Reuters Top News
    "https://feeds.reuters.com/reuters/businessNews",  # Reuters Business
    "https://feeds.reuters.com/reuters/technologyNews",  # Reuters Technology
    "https://bloomberg.com/feed",  # Bloomberg (可能需要适配)
    "https://www.wsj.com/xml/rss/3_7085.xml",  # Wall Street Journal (可能需要适配)

    # 科技媒体 (新增)
    "https://www.theverge.com/rss/index.xml",  # The Verge
    "https://arstechnica.com/feed/",  # Ars Technica

    # 投资机构和数据库 (新增)
    "https://www.cbinsights.com/blog/feed/",  # CB Insights
    "https://techcrunch.com/startups/",  # TechCrunch Startups
    "https://www.crunchbase.com/feed",  # Crunchbase (可能需要适配)

    # AI研究机构 (新增)
    "https://stability.ai/rss",  # Stability AI
    "https://huggingface.co/blog/feed.xml",  # Hugging Face Blog

    # 商业领袖和企业高管 (新增)
    "https://www.tesla.com/blog/rss",  # Tesla Blog
    "https://about.twitter.com/content/dam/about-twitter/company/news/rss-feeds/official-company-blog-rss.xml",  # Twitter Blog (X)
    "https://www.spacex.com/static/releases/feed.xml",  # SpaceX Releases

    # 加密货币和区块链 (新增)
    "https://cointelegraph.com/feed",  # Cointelegraph
    "https://decrypt.co/feed",  # Decrypt
    "https://messari.io/feed.xml",  # Messari
    "https://theblock.co/rss",  # The Block

    # 交易和投资平台 (新增)
    "https://www.binance.com/en/blog/rss",  # Binance Blog
    "https://blog.coinbase.com/feed",  # Coinbase Blog

    # 区块链协议 (新增)
    "https://blog.ethereum.org/feed.xml",  # Ethereum Blog
    "https://polkadot.network/feed/",  # Polkadot Blog

    # 金融和投资 (新增)
    "https://seekingalpha.com/feed.xml",  # Seeking Alpha
    "https://www.ft.com/?format=rss",  # Financial Times (可能需要适配)

    # 亚马逊相关 (新增)
    "https://www.aboutamazon.com/news/rss-feed.xml",  # Amazon Newsroom

    # 马斯克相关 (新增)
    "https://www.neuralink.com/blog.rss",  # Neuralink Blog
    "https://www.boringcompany.com/blog",  # The Boring Company Blog (可能需要适配)

    # 其他AI公司 (新增)
    "https://www.anthropic.com/rss",  # Anthropic Blog
    "https://deepmind.google/rss/",  # DeepMind Blog
    "https://aws.amazon.com/blogs/aws/feed/",  # AWS Blog
    "https://www.amd.com/en/press-room/press-releases.rss",  # AMD Press Releases

    # 补充更多国内大型互联网公司官网 (新增)
    "https://www.hikvision.com/cn/support/download_center_hcsoftware/",  # 海康威视
    "https://www.h3c.com/cn/About_H3C/Company_News/",  # 紫光华山科技(H3C)
    "https://www.lenovo.com.cn/rss",  # 联想中国官网RSS
    "https://www.huawei.com/en/press-events/news",  # 华为新闻 (可能需要适配)
    "https://www.zte.com.cn/global/rss",  # 中兴通讯RSS
    "https://www.xcmg.com/rss",  # 徐工集团RSS
    "https://www.shaoling.com/rss",  # 晶科能源RSS (可能需要适配)
    "https://www.longigroup.com/rss",  # 隆基绿能RSS (可能需要适配)
    "https://www.egretta.com/rss",  # 亿纬锂能RSS (可能需要适配)
    "https://www.ciming.com/rss",  # 晨鸣纸业RSS (可能需要适配)
    "https://www.wuliangye.com.cn/rss",  # 五粮液RSS (可能需要适配)
    "https://www.wanhua.com.cn/rss",  # 万华化学RSS (可能需要适配)
    "https://www.yili.com/rss",  # 伊利集团RSS (可能需要适配)
    "https://www.midea.com/rss",  # 美的集团RSS (可能需要适配)
    "https://www.haier.com/rss",  # 海尔集团RSS (可能需要适配)
    "https://www.gree.com/rss",  # 格力电器RSS (可能需要适配)
    "https://www.fortive.com/rss",  # 江苏恒瑞医药RSS (可能需要适配)
    "https://www.chinaunicom.com/rss",  # 中国联通RSS (可能需要适配)
    "https://www.chinamobile.com/rss",  # 中国移动RSS (可能需要适配)
    "https://www.chinatelecom.com.cn/rss",  # 中国电信RSS (可能需要适配)
    "https://www.sinopec.com/rss",  # 中石化RSS (可能需要适配)
    "https://www.cnpc.com.cn/rss",  # 中石油RSS (可能需要适配)
    "https://www.cscec.com/rss",  # 中国建筑RSS (可能需要适配)
    "https://www.crc.com.hk/rss",  # 华润集团RSS (可能需要适配)
    "https://www.avic.com.cn/rss",  # 中航工业RSS (可能需要适配)
    "https://www.cetc.com.cn/rss",  # 中国电科RSS (可能需要适配)
    "https://www.sinopharm.com/rss",  # 国药集团RSS (可能需要适配)
    "https://www.cofco.com/rss",  # 中粮集团RSS (可能需要适配)
    "https://www.stategrid.com.cn/rss",  # 国家电网RSS (可能需要适配)
    "https://www.crecg.com/rss",  # 中国中铁RSS (可能需要适配)
    "https://www.crcc.cn/rss",  # 中国铁建RSS (可能需要适配)
    "https://www.powerchina.cn/rss",  # 中国电力建设RSS (可能需要适配)
    "https://www.cgnpc.com.cn/rss",  # 中广核RSS (可能需要适配)
    "https://www.citic.com/rss",  # 中信集团RSS (可能需要适配)
    "https://www.polygroup.com/rss",  # 保利集团RSS (可能需要适配)
    "https://www.avic.com.cn/rss",  # 中航集团RSS (可能需要适配)
    "https://www.cosco.com/rss",  # 中远海运RSS (可能需要适配)
    "https://www.baosteel.com/rss",  # 宝钢股份RSS (可能需要适配)
    "https://www.baowu.com/rss",  # 中国宝武钢铁RSS (可能需要适配)
    "https://www.aluminum.com.cn/rss",  # 中国铝业RSS (可能需要适配)
    "https://www.minmetals.com.cn/rss",  # 中国五矿RSS (可能需要适配)
    "https://www.jnmc.com/rss",  # 江西铜业RSS (可能需要适配)
    "https://www.yntc.com.cn/rss",  # 云南铜业RSS (可能需要适配)
    "https://www.goldgroup.com.cn/rss",  # 紫金矿业RSS (可能需要适配)
    "https://www.shandongsteel.com/rss",  # 山东钢铁RSS (可能需要适配)
    "https://www.handanshiron.com/rss",  # 邯钢RSS (可能需要适配)
    "https://www.wisco.com.cn/rss",  # 武钢RSS (可能需要适配)
    "https://www.masteel.com.cn/rss",  # 马钢RSS (可能需要适配)
    "https://www.baotisteel.com/rss",  # 包钢RSS (可能需要适配)
    "https://www.vale.com/rss",  # 河钢RSS (可能需要适配)
    "https://www.posco.com/rss",  # 沙钢RSS (可能需要适配)
    "https://www.arcelormittal.com/rss",  # 首钢RSS (可能需要适配)
    "https://www.nipponsteel.com/rss",  # 鞍钢RSS (可能需要适配)
    "https://www.ssab.com/rss",  # 本钢RSS (可能需要适配)
    "https://www.tatasteel.com/rss",  # 重钢RSS (可能需要适配)
    "https://www.ussteel.com/rss",  # 柳钢RSS (可能需要适配)
    "https://www.aksteel.com/rss",  # 新钢RSS (可能需要适配)
    "https://www.evraz.com/rss",  # 南钢RSS (可能需要适配)
    "https://www.voestalpine.com/rss",  # 华菱钢铁RSS (可能需要适配)
    "https://www.jfe-steel.co.jp/rss",  # 八一钢铁RSS (可能需要适配)
    "https://www.dxsteel.com/rss",  # 方大特钢RSS (可能需要适配)
    "https://www.zhonggang.com/rss",  # 中钢RSS (可能需要适配)
    "https://www.xianggang.com/rss",  # 湘钢RSS (可能需要适配)
    "https://www.liuzhou.com/rss",  # 柳钢RSS (可能需要适配)
    "https://www.maanshan.com/rss",  # 马钢RSS (可能需要适配)
    "https://www.tianjin.com/rss",  # 天津钢管RSS (可能需要适配)
    "https://www.baoji.com/rss",  # 宝鸡钢管RSS (可能需要适配)
    "https://www.chengdu.com/rss",  # 成都无缝钢管RSS (可能需要适配)
    "https://www.wuhan.com/rss",  # 武汉钢铁RSS (可能需要适配)
    "https://www.nanjing.com/rss",  # 南京钢铁RSS (可能需要适配)
    "https://www.xuzhou.com/rss",  # 徐州钢铁RSS (可能需要适配)
    "https://www.jinan.com/rss",  # 济南钢铁RSS (可能需要适配)
    "https://www.qingdao.com/rss",  # 青岛钢铁RSS (可能需要适配)
    "https://www.dalian.com/rss",  # 大连钢铁RSS (可能需要适配)
    "https://www.xiamen.com/rss",  # 厦门钢铁RSS (可能需要适配)
    "https://www.sanya.com/rss",  # 三亚钢铁RSS (可能需要适配)
    "https://www.hainan.com/rss",  # 海南钢铁RSS (可能需要适配)
    "https://www.xinjiang.com/rss",  # 新疆钢铁RSS (可能需要适配)
    "https://www.gansu.com/rss",  # 甘肃钢铁RSS (可能需要适配)
    "https://www.qinghai.com/rss",  # 青海钢铁RSS (可能需要适配)
    "https://www.ningxia.com/rss",  # 宁夏钢铁RSS (可能需要适配)
    "https://www.shaanxi.com/rss",  # 陕西钢铁RSS (可能需要适配)
    "https://www.sichuan.com/rss",  # 四川钢铁RSS (可能需要适配)
    "https://www.guizhou.com/rss",  # 贵州钢铁RSS (可能需要适配)
    "https://www.yunnan.com/rss",  # 云南钢铁RSS (可能需要适配)
    "https://www.chongqing.com/rss",  # 重庆钢铁RSS (可能需要适配)
    "https://www.hubei.com/rss",  # 湖北钢铁RSS (可能需要适配)
    "https://www.hunan.com/rss",  # 湖南钢铁RSS (可能需要适配)
    "https://www.jiangxi.com/rss",  # 江西钢铁RSS (可能需要适配)
    "https://www.fujian.com/rss",  # 福建钢铁RSS (可能需要适配)
    "https://www.guangdong.com/rss",  # 广东钢铁RSS (可能需要适配)
    "https://www.guangxi.com/rss",  # 广西钢铁RSS (可能需要适配)
    "https://www.hainansteel.com/rss",  # 海南钢铁RSS (可能需要适配)
    "https://www.tibet.com/rss",  # 西藏钢铁RSS (可能需要适配)
    "https://www.innermongolia.com/rss",  # 内蒙古钢铁RSS (可能需要适配)
    "https://www.xinjiangsteel.com/rss",  # 新疆钢铁RSS (可能需要适配)
    "https://www.liaoning.com/rss",  # 辽宁钢铁RSS (可能需要适配)
    "https://www.jilin.com/rss",  # 吉林钢铁RSS (可能需要适配)
    "https://www.heilongjiang.com/rss",  # 黑龙江钢铁RSS (可能需要适配)
    "https://www.hebei.com/rss",  # 河北钢铁RSS (可能需要适配)
    "https://www.shanxi.com/rss",  # 山西钢铁RSS (可能需要适配)
    "https://www.anhui.com/rss",  # 安徽钢铁RSS (可能需要适配)
    "https://www.henan.com/rss",  # 河南钢铁RSS (可能需要适配)
    "https://www.shandongsteel.com/rss",  # 山东钢铁RSS (可能需要适配)
    "https://www.jiangsu.com/rss",  # 江苏钢铁RSS (可能需要适配)
    "https://www.zhejiang.com/rss",  # 浙江钢铁RSS (可能需要适配)
    "https://www.shanghai.com/rss",  # 上海钢铁RSS (可能需要适配)
    "https://www.beijing.com/rss",  # 北京钢铁RSS (可能需要适配)
    "https://www.tianjinsteel.com/rss",  # 天津钢铁RSS (可能需要适配)
    "https://www.chinacoal.com.cn/rss",  # 中煤集团RSS (可能需要适配)
    "https://www.cctg.com.cn/rss",  # 国家能源集团RSS (可能需要适配)
    "https://www.shenhuagroup.com.cn/rss",  # 神华集团RSS (可能需要适配)
    "https://www.crec.com.cn/rss",  # 中国能建RSS (可能需要适配)
    "https://www.eht.net.cn/rss",  # 中国电建RSS (可能需要适配)
    "https://www.powerchina.com/rss",  # 中国电力建设RSS (可能需要适配)
    "https://www.cnpower.com.cn/rss",  # 中国电力RSS (可能需要适配)
    "https://www.cgcct.com/rss",  # 中国化学工程RSS (可能需要适配)
    "https://www.sinchem.com.cn/rss",  # 中国化学RSS (可能需要适配)
    "https://www.cnbm.com.cn/rss",  # 中国建材RSS (可能需要适配)
    "https://www.sinoma.com.cn/rss",  # 中材集团RSS (可能需要适配)
    "https://www.jinjiang.com/rss",  # 锦江国际RSS (可能需要适配)
    "https://www.shougang.com/rss",  # 首钢集团RSS (可能需要适配)
    "https://www.ansteel.com/rss",  # 鞍钢集团RSS (可能需要适配)
    "https://www.benxi.com/rss",  # 本钢集团RSS (可能需要适配)
    "https://www.chenggang.com/rss",  # 承钢RSS (可能需要适配)
    "https://www.tanggang.com/rss",  # 唐钢RSS (可能需要适配)
    "https://www.xingang.com/rss",  # 新钢RSS (可能需要适配)
    "https://www.nangang.com/rss",  # 南钢RSS (可能需要适配)
    "https://www.huagang.com/rss",  # 华菱钢铁RSS (可能需要适配)
    "https://www.bagang.com/rss",  # 八一钢铁RSS (可能需要适配)
    "https://www.fangda.com/rss",  # 方大特钢RSS (可能需要适配)
    "https://www.zhonggangsteel.com/rss",  # 中钢RSS (可能需要适配)
    "https://www.xianggangsteel.com/rss",  # 湘钢RSS (可能需要适配)
    "https://www.liugang.com/rss",  # 柳钢RSS (可能需要适配)
    "https://www.mastesteel.com/rss",  # 马钢RSS (可能需要适配)
    "https://www.tianjinteel.com/rss",  # 天津钢管RSS (可能需要适配)
    "https://www.baojisteel.com/rss",  # 宝鸡钢管RSS (可能需要适配)
    "https://www.chengdusteel.com/rss",  # 成都无缝钢管RSS (可能需要适配)
    "https://www.wuhang.com/rss",  # 武汉钢铁RSS (可能需要适配)
    "https://www.nanjingsteel.com/rss",  # 南京钢铁RSS (可能需要适配)
    "https://www.xuzhusteel.com/rss",  # 徐州钢铁RSS (可能需要适配)
    "https://www.jinangang.com/rss",  # 济南钢铁RSS (可能需要适配)
    "https://www.qingdaosteel.com/rss",  # 青岛钢铁RSS (可能需要适配)
    "https://www.daliansteel.com/rss",  # 大连钢铁RSS (可能需要适配)
    "https://www.xiamengang.com/rss",  # 厦门钢铁RSS (可能需要适配)
    "https://www.sanyasteel.com/rss",  # 三亚钢铁RSS (可能需要适配)
    "https://www.hainangang.com/rss",  # 海南钢铁RSS (可能需要适配)
    "https://www.xinjiangsteel.com/rss",  # 新疆钢铁RSS (可能需要适配)
    "https://www.gansugang.com/rss",  # 甘肃钢铁RSS (可能需要适配)
    "https://www.qinghaisteel.com/rss",  # 青海钢铁RSS (可能需要适配)
    "https://www.ningxiagang.com/rss",  # 宁夏钢铁RSS (可能需要适配)
    "https://www.shanxisteel.com/rss",  # 陕西钢铁RSS (可能需要适配)
    "https://www.sichuansteel.com/rss",  # 四川钢铁RSS (可能需要适配)
    "https://www.guizhouteel.com/rss",  # 贵州钢铁RSS (可能需要适配)
    "https://www.yunnangang.com/rss",  # 云南钢铁RSS (可能需要适配)
    "https://www.chongqingsteel.com/rss",  # 重庆钢铁RSS (可能需要适配)
    "https://www.hubeisteel.com/rss",  # 湖北钢铁RSS (可能需要适配)
    "https://www.hunangang.com/rss",  # 湖南钢铁RSS (可能需要适配)
    "https://www.jiangxigang.com/rss",  # 江西钢铁RSS (可能需要适配)
    "https://www.fujiansteel.com/rss",  # 福建钢铁RSS (可能需要适配)
    "https://www.guangdongsteel.com/rss",  # 广东钢铁RSS (可能需要适配)
    "https://www.guangxigang.com/rss",  # 广西钢铁RSS (可能需要适配)
    "https://www.hainangangye.com/rss",  # 海南钢铁RSS (可能需要适配)
    "https://www.tibetsteel.com/rss",  # 西藏钢铁RSS (可能需要适配)
    "https://www.neimenggugang.com/rss",  # 内蒙古钢铁RSS (可能需要适配)
    "https://www.liaonangang.com/rss",  # 辽宁钢铁RSS (可能需要适配)
    "https://www.jilingang.com/rss",  # 吉林钢铁RSS (可能需要适配)
    "https://www.heilongjianggang.com/rss",  # 黑龙江钢铁RSS (可能需要适配)
    "https://www.hebeigang.com/rss",  # 河北钢铁RSS (可能需要适配)
    "https://www.shanxigang.com/rss",  # 山西钢铁RSS (可能需要适配)
    "https://www.anhuigang.com/rss",  # 安徽钢铁RSS (可能需要适配)
    "https://www.henangang.com/rss",  # 河南钢铁RSS (可能需要适配)
    "https://www.shandonggang.com/rss",  # 山东钢铁RSS (可能需要适配)
    "https://www.jiangsugang.com/rss",  # 江苏钢铁RSS (可能需要适配)
    "https://www.zhejianggang.com/rss",  # 浙江钢铁RSS (可能需要适配)
    "https://www.shanghaigang.com/rss",  # 上海钢铁RSS (可能需要适配)
    "https://www.beijinggang.com/rss",  # 北京钢铁RSS (可能需要适配)
    "https://www.tianjingang.com/rss",  # 天津钢铁RSS (可能需要适配)
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

# 缓存管理
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
    clean_message = clean_message.replace('---', '\n')  # 移除分隔线，只保留换行
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
                    "content": f"🌍 全球情报与金融分析日报 | {time.strftime('%Y-%m-%d')}",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": clean_message
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

async def extract_news_items() -> List[Dict[str, str]]:
    """
    从多个RSS源提取新闻条目，并按重要性排序
    使用增强版采集器，支持API优先、Playwright抓取等多种策略
    
    Returns:
        新闻条目列表，每个包含title, summary, link, importance_score
    """
    # 从环境变量获取API密钥
    api_keys = {
        'MARKETAUX_API_KEY': os.environ.get('MARKETAUX_API_KEY', ''),
        'POLYGON_API_KEY': os.environ.get('POLYGON_API_KEY', '')
    }
    
    # 创建增强版采集器实例
    fetcher = EnhancedRSSFetcher(api_keys)
    
    # 执行多层采集策略
    all_raw_articles = await fetcher.fetch_all()
    
    # 去重处理
    unique_articles = fetcher.deduplicate_articles(all_raw_articles)
    
    # 加载已处理的URL缓存
    processed_urls = load_cache()
    
    # 过滤掉已处理过的文章
    fresh_articles = [article for article in unique_articles if article.get('link', '') not in processed_urls]
    
    # 为每篇文章计算重要性分数
    articles_with_scores = []
    for article in fresh_articles:
        title = article.get('title', '').strip()
        summary = article.get('description', '').strip()
        link = article.get('link', '')
        published_time = article.get('published', None)
        
        # 跳过空标题的文章
        if not title:
            continue
            
        # 清理summary中的HTML标签
        import re
        summary = re.sub(r'<[^>]+>', '', summary)
        summary = summary[:200] + '...' if len(summary) > 200 else summary
        
        # 检查是否为必杀新闻（不感兴趣的内容）
        if is_boring_news(title, summary):
            logger.info(f"🚫 过滤掉不感兴趣的新闻: {title[:50]}...")
            continue
        
        # 检查是否为必选新闻（特别关注的内容）
        is_domestic = is_domestic_news(title, summary)
        is_finance = is_finance_news(title, summary)
        is_ai_tech = is_ai_tech_news(title, summary)
        is_crypto = is_crypto_news(title, summary)
        is_energy = is_energy_news(title, summary)
        
        # 计算新闻重要性分数
        importance_score = calculate_importance_score(title, summary, link, published_time, {}, is_domestic, is_finance, is_ai_tech, is_crypto, is_energy)
        
        # 只处理重要性得分大于等于3的新闻，或者包含中国相关内容的新闻
        if importance_score < 3 and '中国' not in title and 'China' not in title.lower():
            logger.info(f"🟡 低重要性新闻，跳过: {title[:50]}...")
            continue
        
        articles_with_scores.append({
            'title': title,
            'summary': summary,
            'link': link,
            'importance_score': importance_score
        })
    
    # 按重要性分数降序排序
    articles_with_scores.sort(key=lambda x: x['importance_score'], reverse=True)
    
    # 更新缓存，添加新处理的URL
    for item in articles_with_scores:
        processed_urls.add(item['link'])
    save_cache(processed_urls)
    
    logger.info(f"总共提取到 {len(articles_with_scores)} 条新鲜新闻，并按重要性排序")
    return articles_with_scores[:20]  # 最多处理20条新闻

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
        SYSTEM_PROMPT = """你是一名拥有全球视野的**顶级宏观策略师**（Ray Dalio/Soros 风格）。你的客户是时间宝贵、渴望深度认知但厌恶晦涩术语的中国高净值投资者。

你的核心任务是：**像主编一样筛选新闻，像操盘手一样拆解利益，用最通俗的语言输出高密度情报。**

# 🚦 智能分级协议 (Triage Protocol)

在分析每条新闻前，先进行内部评分（1-10分）：
* **🔴 重磅 (8-10分)**：涉及行业格局剧变、核心技术突破、重大地缘/法律落地。-> **启用【深度穿透模式】** (字数 550-750字)
* **🟡 一般 (4-7分)**：常规财报、产品迭代、普通合作。-> **启用【快讯速读模式】** (字数 <250字)
* **🟢 噪音 (1-3分)**：纯公关软文、无实质内容的言论、捕风捉影。-> **直接丢弃，不输出**。

---

# Output Format (根据评分选择)

## 🔴 模式 A：深度穿透 (针对 8-10 分重磅新闻)
*要求：必须包含信源评级、反身性推演、Gartner周期、历史对照。语言要通俗易懂（说人话）。*

### [🔥重磅 | 情绪分 1-5] 新闻标题 (突显核心矛盾)
> [🔗 来源](URL)
> 📅 **周期定位**：[Gartner曲线：期望膨胀/泡沫破裂/稳步爬升]
> 📡 **信源评级**：[一级(官方文件) / 二级(权威媒体) / 三级(小道消息)]

**1. 🕵️ 信号与动机 (The Truth)**
* **核心事实**：(剥离公关话术，只看物理动作。例如：是"发布Demo(噪音)"还是"降低90%成本(信号)"？)
* **利益/动机**：(谁在做局？是为了融资变现、政治选票，还是掩盖利空？)
* **判别结论**：**[信号 ✅ / 噪音 ❌]** (理由：是否改变了供需或竞争格局？)

**2. 🕰️ 历史对照 (History Rhymes)**
* **历史剧本**：(精准匹配过去的危机或机遇，如美日半导体战、互联网泡沫。若无，标注"技术奇点无参照")
* **剧本推演**：(参考历史，接下来的标准剧情走向是什么？)

**3. 🦋 三层连锁反应 (Chain Reaction 3.0)**
* **第一层 (物理层)**：直接受影响的上下游、价格波动。
* **第二层 (逻辑层)**：由第一层引发的产业替代、成本转移。
* **第三层 (反身性/索罗斯博弈)**：**(最关键 - 必须通俗解释)**
    * *预期自我实现/毁灭*：市场的一致性预期是否过热？（例如：人人抢购电力股 -> 产能疯狂扩张 -> 导致过剩 -> 崩盘）。
    * *主力博弈信号*：**检查"利好滞涨"**。如果这是重大利好，但股价不涨（或高开低走），是否说明主力在借利好出货（Sell the News）？

**4. 🇨🇳 中国影响 (Impact Analysis)**
* **⚡ 短期阵痛**：(对A股情绪、汇率、打工人饭碗的即时冲击)
* **🏛 长期国运**：(是否倒逼自主可控？还是被锁死？)

**5. 💰 资金流向 (Investment Action)**
* **📈 潜在赢家**：[板块/龙头] (逻辑：护城河加深)
* **📉 潜在输家**：[板块/概念] (逻辑：逻辑证伪)
* **🛡 策略建议**：(结合"市场反应"给出建议。例如：利好滞涨则立即减仓；利空不跌则左侧买入。)

---

## 🟡 模式 B：快讯速读 (针对 4-7 分常规新闻)
*要求：极度精简，一针见血。*

### [📝速读 | 情绪分 1-5] 新闻标题
> [🔗 来源](URL) | 📡 **信源**：[一级/二级/三级]
* **⚡ 核心逻辑**：(发生了什么？为什么重要？)
* **💰 钱袋子影响**：(直接利好/利空哪个板块？对打工人有什么影响？)

---

# Constraints & Style Guide
1.  **中国视角**：所有分析落脚点必须是人民币资产、中国国运和打工人的存量财富。
2.  **说人话 (Humanize)**：避免堆砌金融术语。解释复杂概念时，多用生活中的类比（如：把"产能过剩"比作"种苹果的太多了"）。
3.  **盘口思维**：在分析投资建议时，必须应用**"利好不涨即利空"**的逻辑，警惕接盘。
4.  **合并同类项**：如果多条新闻讲的是同一件事（如财报+股价变动），请合并为一个模块输出。"""

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

def calculate_importance_score(title: str, summary: str, source_url: str, published_time, source_weights: dict, is_domestic: bool = False, is_finance: bool = False, is_ai_tech: bool = False, is_crypto: bool = False, is_energy: bool = False) -> float:
    """
    计算新闻重要性分数
    
    Args:
        title: 新闻标题
        summary: 新闻摘要
        source_url: 新闻来源URL
        published_time: 发布时间
        source_weights: 来源权重字典
        is_domestic: 是否为中国国内新闻
        is_finance: 是否为金融新闻
        is_ai_tech: 是否为AI科技新闻
        is_crypto: 是否为加密货币新闻
        is_energy: 是否为能源新闻
    
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
    if published_time and isinstance(published_time, (tuple, list)) and len(published_time) >= 6:
        try:
            pub_date = datetime.datetime(*published_time[:6])
            now = datetime.datetime.now()
            hours_diff = (now - pub_date).total_seconds() / 3600
            if hours_diff <= 24:  # 24小时内发布的新闻
                score += 1.0
            elif hours_diff <= 48:  # 48小时内发布的新闻
                score += 0.5
        except (ValueError, TypeError):
            # 如果时间解析失败，跳过时间因素评分
            pass
    elif published_time and isinstance(published_time, (int, float)):
        # 如果published_time是时间戳
        try:
            pub_date = datetime.datetime.fromtimestamp(published_time)
            now = datetime.datetime.now()
            hours_diff = (now - pub_date).total_seconds() / 3600
            if hours_diff <= 24:  # 24小时内发布的新闻
                score += 1.0
            elif hours_diff <= 48:  # 48小时内发布的新闻
                score += 0.5
        except (ValueError, TypeError, OSError):
            # 如果时间戳解析失败，跳过时间因素评分
            pass
    
    # 5. 标题长度和特征 (标题长度适中且包含数字或符号可能更重要)
    if 30 < len(title) < 100:  # 标题长度适中
        score += 0.5
    if ':' in title or '-' in title:  # 包含分隔符
        score += 0.3
    if any(char.isdigit() for char in title):  # 包含数字
        score += 0.2
    
    # 6. 特定新闻类型加分
    if is_domestic:
        score += 1.0  # 国内新闻额外加分
    if is_finance:
        score += 1.5  # 金融新闻额外加分
    if is_ai_tech:
        score += 1.2  # AI科技新闻额外加分
    if is_crypto:
        score += 1.0  # 加密货币新闻额外加分
    if is_energy:
        score += 0.8  # 能源新闻额外加分
    
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
        import asyncio
        news_items = asyncio.run(extract_news_items())
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

def is_boring_news(title: str, summary: str) -> bool:
    """
    检查是否为不感兴趣的新闻（必杀新闻过滤器）
    """
    boring_keywords = [
        '广告', '推广', '营销', '招聘', '求职', '招聘启事', '促销', '打折', '优惠',
        '娱乐', '明星', '八卦', '综艺', '电视剧', '电影', '音乐', '演唱会',
        '体育', '足球', '篮球', '比赛', '冠军', '体育赛事', '奥运会', '世界杯',
        '游戏', '手游', '电竞', '游戏攻略', '游戏评测', '游戏更新',
        '美食', '旅游', '景点', '攻略', '酒店', '民宿', '度假', '旅行',
        '时尚', '美容', '护肤', '穿搭', '美妆', '奢侈品', '时装周',
        '健康', '养生', '保健', '医疗', '医院', '医生', '药品', '治疗',
        '教育', '学校', '学生', '考试', '高考', '大学', '留学', '培训',
        '房产', '房价', '楼盘', '房地产', '购房', '租房', '物业', '装修',
        '汽车', '新车', '汽车评测', '汽车资讯', '驾驶', '保养', '维修',
        '宠物', '动物', '动物园', '野生动物', '保护动物', '救助',
        '天气', '预报', '气温', '降雨', '雾霾', '空气质量', '污染',
        '节日', '庆祝', '庆典', '纪念日', '生日', '结婚', '婚礼', '离婚',
        '宗教', '信仰', '教堂', '寺庙', '佛教', '基督教', '伊斯兰教',
        '政治', '选举', '总统', '总理', '政府', '议会', '国会', '政党',
        '军事', '军队', '士兵', '武器', '导弹', '战机', '军舰', '战争',
        '暴力', '犯罪', '抢劫', '盗窃', '杀人', '谋杀', '绑架', '恐怖主义',
        '色情', '低俗', '露骨', '暴露', '性感', '诱惑', '情色', '黄色',
        '谣言', '传言', '小道消息', '未经证实', '疑似', '据说', '听说'
    ]
    
    text = (title + ' ' + summary).lower()
    for keyword in boring_keywords:
        if keyword in text:
            return True
    return False

def is_domestic_news(title: str, summary: str) -> bool:
    """
    检查是否为中国国内新闻
    """
    domestic_keywords = [
        '中国', '中华人民共和国', '北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '武汉', '西安', '重庆',
        '中国内地', '中国大陆', '国内', '中央', '国务院', '发改委', '央行', '证监会', '银保监会', '外汇局',
        '人大', '政协', '中共', '共产党', '总书记', '主席', '总理', '部长', '省长', '市长', '书记',
        'a股', '港股', '沪深', '上证', '深证', '创业板', '科创板', '北交所', '新三板', '中概股',
        '人民币', 'cny', 'rmb', '汇率', '外汇', '国债', '地方债', '城投债', '利率', '存款',
        '房贷', '车贷', '消费贷', '信用卡', '支付宝', '微信支付', '移动支付', '数字货币', '数字人民币',
        '国企', '央企', '民企', '私企', '外企', '合资', '独资', '股份制', '上市公司', 'ipo',
        '税收', '财政', '预算', '决算', '社保', '医保', '公积金', '养老金', '失业金', '低保',
        '教育', '医疗', '住房', '养老', '就业', '创业', '创新', '科技', '研发', '专利', '商标',
        '环保', '污染', '治理', '生态', '绿色', '节能', '减排', '碳中和', '碳达峰', '新能源',
        '交通', '高铁', '地铁', '公交', '航空', '机场', '港口', '物流', '快递', '外卖', '电商',
        '农业', '农村', '农民', '土地', '粮食', '蔬菜', '水果', '养殖', '渔业', '林业',
        '工业', '制造业', '工厂', '工人', '生产', '制造', '加工', '出口', '进口', '贸易',
        '互联网', '电商', '直播', '短视频', '社交', '媒体', '新闻', '出版', '广播', '电视',
        '华为', '腾讯', '阿里', '百度', '字节', '美团', '滴滴', '京东', '拼多多', '小米',
        '中石油', '中石化', '国家电网', '中国移动', '中国联通', '中国电信', '工商银行', '建设银行', '农业银行', '中国银行'
    ]
    
    text = (title + ' ' + summary).lower()
    for keyword in domestic_keywords:
        if keyword in text:
            return True
    return False

def is_finance_news(title: str, summary: str) -> bool:
    """
    检查是否为金融新闻
    """
    finance_keywords = [
        '金融', '银行', '证券', '保险', '基金', '信托', '期货', '期权', '外汇', '黄金', '白银', '贵金属',
        '股票', '股市', '股价', '涨跌', '涨停', '跌停', '停牌', '复牌', 'ipo', '退市', '重组', '并购',
        '财报', '业绩', '盈利', '亏损', '营收', '利润', '市值', '市盈率', '市净率', '净资产', '收益率',
        '央行', '美联储', '欧央行', '日央行', '货币政策', '利率', '加息', '降息', '量化宽松', '紧缩',
        '通胀', '通货膨胀', 'cpi', 'ppi', 'gdp', 'pmi', '失业率', '就业', '财政', '税收', '预算',
        '债券', '国债', '企业债', '可转债', '信用债', '利率债', '发行', '兑付', '违约', '评级',
        '投资', '理财', '收益', '风险', '回报', '资产', '负债', '现金流', '融资', '融券', '杠杆',
        '期权', '期货', '衍生品', '对冲', '套利', '投机', '做多', '做空', '止损', '止盈',
        'ipo', '打新', '配售', '申购', '中签', '破发', '上市', '退市', '摘牌', '停牌', '复牌',
        '机构', '券商', '投行', '资管', '私募', '公募', 'vc', 'pe', '风投', '天使投资', 'a轮', 'b轮',
        '比特币', '以太坊', '加密货币', '数字货币', '区块链', '挖矿', '交易所', '钱包', '合约',
        '美元', '欧元', '英镑', '日元', '汇率', '外汇', '储备', '储备货币', '国际化', '结算',
        '纳斯达克', '标普500', '道琼斯', '恒生', '上证', '深证', '创业板', '科创板', '主板', '中小板',
        '摩根', '高盛', '花旗', '汇丰', '瑞银', '德意志', '巴克莱', '法巴', '三菱', '三井',
        '巴菲特', '索罗斯', '达利欧', '桥水', '文艺复兴', '千禧年', '城堡', '绿光', '老虎'
    ]
    
    text = (title + ' ' + summary).lower()
    for keyword in finance_keywords:
        if keyword in text:
            return True
    return False

def is_ai_tech_news(title: str, summary: str) -> bool:
    """
    检查是否为AI科技新闻
    """
    ai_tech_keywords = [
        '人工智能', 'ai', '机器学习', '深度学习', '神经网络', '算法', '大数据', '云计算', '物联网', '5g', '6g',
        '芯片', '半导体', '集成电路', 'gpu', 'cpu', 'npu', 'tpu', '英伟达', 'amd', '英特尔', '高通', '联发科',
        '谷歌', 'google', '微软', 'apple', '苹果', 'facebook', 'meta', '亚马逊', 'amazon', 'netflix', '特斯拉', 'tesla',
        'openai', 'gpt', 'chatgpt', 'copilot', 'midjourney', 'stable diffusion', '扩散模型', 'transformer',
        '自动驾驶', '机器人', '无人机', 'vr', 'ar', 'mr', '虚拟现实', '增强现实', '混合现实', '元宇宙',
        '量子计算', '量子通信', '生物识别', '人脸识别', '语音识别', '自然语言处理', '计算机视觉', '模式识别',
        '开源', 'github', 'gitlab', '编程', '软件', '硬件', '操作系统', 'linux', 'windows', 'macos',
        '手机', '智能手机', '平板', '电脑', '笔记本', '服务器', '数据中心', '边缘计算', '雾计算',
        '网络安全', '信息安全', '隐私保护', '加密', '区块链', '分布式', '共识算法', '智能合约',
        '自动驾驶', '无人车', '飞行汽车', '电动汽车', '电池', '充电桩', '续航', '快充', '无线充电',
        '传感器', '摄像头', '激光雷达', '毫米波雷达', '超声波雷达', '导航', '定位', 'gps', '北斗',
        '智能音箱', '智能家居', '智能手表', '智能眼镜', '可穿戴设备', '智能家电', '智能门锁', '智能照明',
        '数据中心', '服务器', '存储', '内存', '硬盘', 'ssd', 'hdd', 'raid', '备份', '恢复',
        '虚拟化', '容器', 'docker', 'kubernetes', '云原生', '微服务', 'api', '接口', 'sdk', '开发工具'
    ]
    
    text = (title + ' ' + summary).lower()
    for keyword in ai_tech_keywords:
        if keyword in text:
            return True
    return False

def is_crypto_news(title: str, summary: str) -> bool:
    """
    检查是否为加密货币新闻
    """
    crypto_keywords = [
        '比特币', 'btc', '以太坊', 'eth', '莱特币', 'ltc', '瑞波币', 'xrp', '比特币现金', 'bch', 'eos',
        '加密货币', '数字货币', '虚拟货币', '代币', 'coin', 'token', 'crypto', 'digital currency',
        '区块链', 'blockchain', '分布式账本', '共识机制', '挖矿', 'miner', 'staking', '质押', 'pos', 'pow',
        '交易所', 'exchange', 'binance', '币安', 'huobi', '火币', 'okex', 'gate', 'kucoin', 'coinbase',
        '钱包', 'wallet', '热钱包', '冷钱包', '私钥', '公钥', '助记词', 'keystore', 'metamask', 'imtoken',
        'defi', '去中心化金融', '借贷', 'yield farming', '流动性挖矿', 'amm', '自动做市商', 'lp', '流动性提供者',
        'nft', '非同质化代币', '数字藏品', '艺术品', '收藏品', '游戏道具', '元宇宙', '虚拟土地', 'avatar',
        'ico', 'sto', 'ido', '代币发行', '首次代币发行', '证券型代币发行', '去中心化交易所', 'dex', 'uniswap',
        '稳定币', 'usdt', 'tether', 'usdc', 'dai', '算法稳定币', '抵押稳定币', '中心化稳定币', '去中心化稳定币',
        'layer2', '扩容', '闪电网络', '侧链', '状态通道', 'rollup', 'optimistic', 'zk', '零知识证明',
        '公链', '联盟链', '私有链', '跨链', '桥', 'bridge', '互操作性', 'cosmos', 'polkadot', 'avalanche',
        '监管', '合规', '牌照', '许可证', '反洗钱', 'aml', '了解你的客户', 'kyc', '税务', '征税', '禁止',
        '山寨币', 'altcoin', 'memecoin', '狗狗币', 'doge', '柴犬币', 'shiba', '马斯克', '特斯拉', 'space x'
    ]
    
    text = (title + ' ' + summary).lower()
    for keyword in crypto_keywords:
        if keyword in text:
            return True
    return False

def is_energy_news(title: str, summary: str) -> bool:
    """
    检查是否为能源新闻
    """
    energy_keywords = [
        '石油', '原油', 'wti', '布伦特', 'opec', '欧佩克', '天然气', 'lng', 'cng', '页岩气', '煤层气', '致密气',
        '煤炭', '焦炭', '电力', '电网', '发电', '输电', '配电', '用电', '电价', '电费', '峰谷电价', '阶梯电价',
        '风电', '风力发电', '风机', '海上风电', '陆上风电', '风场', '风能', '风速', '风向', '塔筒', '叶片',
        '光伏', '太阳能', '光伏发电', '组件', '电池片', '硅料', '逆变器', '支架', '跟踪系统', '储能', '电池',
        '核电', '核能', '反应堆', '铀', '钚', '乏燃料', '放射性', '安全壳', '冷却', '核废料', '核聚变', '核裂变',
        '氢能', '氢气', '燃料电池', '电解水', '制氢', '储氢', '运氢', '加氢站', '氢能源汽车', '氢冶金', '绿氢',
        '生物质能', '沼气', '生物柴油', '燃料乙醇', '生物质发电', '垃圾发电', '秸秆', '木屑', '生物燃气',
        '地热能', '潮汐能', '波浪能', '海洋能', '可再生能源', '清洁能源', '绿色能源', '低碳', '零碳', '负碳',
        '碳排放', '碳中和', '碳达峰', '碳交易', '碳市场', '碳足迹', '碳汇', '减排', '节能', '能效', '能耗',
        '能源安全', '能源独立', '能源转型', '能源革命', '能源政策', '能源补贴', '能源税', '能源价格', '能源危机',
        '沙特', '俄罗斯', '美国', '伊朗', '委内瑞拉', '伊拉克', '阿联酋', '挪威', '加拿大', '尼日利亚', '利比亚',
        '中石油', '中石化', '中海油', '国家能源集团', '华能', '国电', '大唐', '华电', '国家电投', '三峡集团', '葛洲坝'
    ]
    
    text = (title + ' ' + summary).lower()
    for keyword in energy_keywords:
        if keyword in text:
            return True
    return False

def send_error_alert(error_message: str, max_retries: int = MAX_RETRIES):
    """
    发送错误警报到飞书（使用webhook方式）
    """
    # 构建错误警报消息
    alert_msg = f"🚨 机器人故障警报\n\n错误详情：{error_message}\n\n请及时检查机器人状态！\n\nDeepSeek-V3 监控系统"
    
    # 使用webhook发送错误警报
    return send_to_feishu_webhook(alert_msg, max_retries)

if __name__ == "__main__":
    main()


