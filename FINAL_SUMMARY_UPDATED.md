# 🚀 每日AI新闻机器人项目总结（更新版）

## 项目概述
这是一个基于Python的自动化新闻抓取、分析和推送系统，利用RSS源获取全球新闻，通过DeepSeek大模型进行智能分析，并将结果推送到飞书群组。

## 核心功能
- ✅ 自动抓取全球主流RSS新闻源
- ✅ 使用DeepSeek大模型进行新闻分析
- ✅ 智能过滤和去重
- ✅ 情绪评分系统
- ✅ 飞书群组推送
- ✅ 定时任务调度
- ✅ 紧急新闻监控
- ✅ 历史记录管理
- ✅ 国内新闻源支持
- ✅ 优化的输出格式
- ✅ 飞书应用认证：支持使用App ID和App Secret进行认证，可发送更丰富的消息格式
- ✅ 专业金融分析师角色：采用桥水基金和高盛联合训练的首席宏观经济分析师身份
- ✅ 标准化分析框架：实现统一的分析结构，包括情绪分、核心事实、底层逻辑和财富影响等维度

## 技术栈
- Python 3.x
- feedparser - RSS解析
- requests - HTTP请求
- DeepSeek API - 大模型分析
- 飞书Webhook - 消息推送
- GitHub Actions - 定时任务

## RSS源配置
- 国际新闻：BBC, CNN, Reuters, NYT等
- 金融财经：CNBC, Yahoo Finance, FT等
- 科技资讯：TechCrunch, Hacker News等
- 加密货币：CoinDesk
- 学术研究：ArXiv AI Papers
- 国内新闻：百度新闻、人民网、新华网、中国新闻网、澎湃新闻等
- 国内财经：腾讯财经、新浪财经、财联社、36氪等

## 文件结构
- `daily_news_bot.py` - 主要的新闻分析和推送机器人
- `urgent_news_monitor.py` - 紧急新闻监控机器人
- `fetch_news.py` - 新闻抓取模块
- `get_daily_news.py` - 获取每日新闻
- `get_today_news_summary.py` - 今日新闻摘要
- `get_morning_to_now_news.py` - 早晨至今新闻
- `morning_to_now_news_report.py` - 早晨至今新闻报告
- `show_processed_news.py` - 显示已处理新闻
- `show_all_processed_news.py` - 显示所有已处理新闻
- `.github/workflows/daily_news.yml` - GitHub Actions工作流
- `history.json` - 历史记录文件
- `lark_config.json` - 飞书配置文件
- `requirements.txt` - 依赖包列表

## 配置要求
- DeepSeek API密钥
- 飞书机器人配置（APP ID, APP Secret, Chat ID）
- 环境变量设置

## 主要改进
1. 添加了国内主流新闻源支持
2. 优化了AI分析提示词，移除了图片生成指令
3. 简化了新闻输出格式
4. 增强了分类系统，包括国内新闻分类
5. 改进了错误处理和调试功能
6. 引入了专业金融分析师角色，采用桥水基金和高盛联合训练的首席宏观经济分析师身份
7. 实现了标准化的分析框架，包括情绪分、核心事实、底层逻辑和财富影响等维度
8. 移除了所有图片处理功能，专注于纯文本分析和报告