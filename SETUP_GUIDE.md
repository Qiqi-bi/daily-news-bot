# 项目配置与运行指南

## 项目可运行性确认

项目已经过优化，可以正常运行。以下是用户需要完成的配置步骤：

## 必需配置

### 1. 环境变量配置

创建 `.env` 文件，配置以下必需的环境变量：

```env
# DeepSeek API密钥（必需）
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 飞书webhook URL（必需）
FEISHU_WEBHOOK_URL=your_feishu_webhook_url_here
```

### 2. 可选配置

以下为可选配置，用于增强功能：

```env
# 金融API密钥（可选，用于获取股票价格）
MARKETAUX_API_KEY=your_marketaux_api_key_here
POLYGON_API_KEY=your_polygon_api_key_here

# Alpha Vantage API密钥（可选）
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here

# Finnhub API密钥（可选）
FINNHUB_API_KEY=your_finnhub_api_key_here
```

## 安装与运行步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium  # 安装Playwright浏览器
```

### 2. 测试运行

```bash
python daily_news_bot.py
```

## 配置说明

### API密钥获取

1. **DeepSeek API密钥**：
   - 访问 https://platform.deepseek.com/
   - 注册账号并获取API密钥

2. **飞书webhook URL**：
   - 在飞书群聊中添加自定义机器人
   - 获取webhook URL

3. **可选API密钥**：
   - Marketaux: https://www.marketaux.com/
   - Polygon: https://polygon.io/
   - Alpha Vantage: https://www.alphavantage.co/
   - Finnhub: https://finnhub.io/

## 项目结构

```
每日AI新闻/
├── daily_news_bot.py          # 主程序文件
├── enhanced_rss_fetcher.py    # 增强版RSS采集器
├── requirements.txt           # 依赖包列表
├── .env                      # 环境变量配置（需自行创建）
├── .gitignore               # Git忽略文件
├── README.md                 # 项目说明
├── PROJECT_SUMMARY.md        # 项目总结
└── SETUP_GUIDE.md           # 本配置指南
```

## 注意事项

1. **隐私保护**：所有敏感信息都通过环境变量配置，不会被提交到Git仓库
2. **代理设置**：代码中已包含代理配置，可根据需要启用/禁用
3. **错误处理**：程序包含完善的错误处理和重试机制
4. **缓存机制**：新闻去重功能通过history.json文件实现

## 测试配置

运行以下命令测试配置是否正确：

```bash
python -c "import os; print('DEEPSEEK_API_KEY存在:', bool(os.environ.get('DEEPSEEK_API_KEY'))); print('FEISHU_WEBHOOK_URL存在:', bool(os.environ.get('FEISHU_WEBHOOK_URL')))"
```

## 常见问题

Q: 程序无法运行怎么办？
A: 检查是否安装了所有依赖包，并确认环境变量已正确配置。

Q: 如何设置定时任务？
A: 可使用系统的定时任务工具（如Linux的cron或Windows任务计划程序）定期运行daily_news_bot.py。

Q: 是否可以在云服务器上运行？
A: 是的，本程序支持在云服务器上运行，只需配置好相应的环境变量即可。