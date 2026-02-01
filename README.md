# 每日AI新闻机器人

这是一个自动抓取、分析和推送AI及相关领域新闻的机器人。它使用增强版RSS采集器，通过多层策略确保最大程度获取有效新闻。

## 功能特点

- **多层采集策略**：API优先、更新后RSS源、Playwright浏览器抓取、传统RSS源四层策略
- **智能分析**：使用LLM进行智能分析和摘要
- **飞书推送**：推送到飞书群组
- **智能去重**：基于标题和链接的智能去重
- **重要性排序**：根据来源和关键词对新闻进行重要性排序

## 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium  # 安装Playwright浏览器
```

## 配置

1. 复制 `.env` 为 `.env` 并填入你的API密钥和飞书Webhook URL：

```bash
MARKETAUX_API_KEY=your_marketax_api_key_here
POLYGON_API_KEY=your_polygon_api_key_here
LARK_WEBHOOK_URL=your_lark_webhook_url_here
```

2. 或者直接在 `lark_config.json` 中配置飞书机器人的Webhook URL。

## 运行

```bash
python daily_news_bot.py
```

或者使用批处理脚本：

```bash
# Windows
start_news_bot.bat

# PowerShell
./run_robot.ps1
```

## 采集策略

机器人采用四层采集策略：

1. **API采集**：优先从MarketAxess、Polygon等API获取数据
2. **更新后RSS源**：抓取已更新的RSS源
3. **Playwright浏览器抓取**：使用无头浏览器抓取反爬虫网站
4. **传统RSS源**：抓取标准RSS源

## 支持的新闻源

- AI/ML博客（Google DeepMind、OpenAI、Anthropic等）
- 科技新闻（TechCrunch、The Verge等）
- 金融新闻（FT、WSJ等）
- 加密货币新闻（CoinDesk、Cointelegraph等）
- 学术论文（arXiv等）

## 系统架构

- `daily_news_bot.py` - 主程序文件
- `enhanced_rss_fetcher.py` - 增强版RSS采集器
- `lark_config.json` - 飞书配置
- `history.json` - 新闻缓存记录
- `requirements.txt` - 依赖包列表
