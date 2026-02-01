# 每日AI新闻机器人 - 项目总结

## 项目概述

这是一个智能新闻采集与分析机器人，能够自动从全球各大新闻源采集信息，使用AI模型进行深度分析，并将结果推送到飞书群组。

## 核心功能

1. **多源采集**：支持RSS、API、Playwright浏览器抓取等多种采集方式
2. **智能分析**：使用DeepSeek等大语言模型对新闻进行深度分析
3. **多层策略**：API优先、RSS源、Playwright抓取、传统RSS四层采集策略
4. **智能去重**：自动过滤重复新闻
5. **重要性排序**：根据新闻来源、关键词等因素计算重要性分数
6. **价格注入**：自动获取相关资产的实时价格
7. **飞书推送**：将分析结果以富文本卡片形式推送到飞书群

## 技术架构

### 主要组件

- `daily_news_bot.py` - 主程序文件
- `enhanced_rss_fetcher.py` - 增强版RSS采集器
- `lark_config.json` - 飞书配置
- `history.json` - 新闻缓存记录
- `requirements.txt` - 依赖包列表

### 采集策略

本项目采用四层采集策略，确保最大程度获取有效新闻：

1. **API优先**：金融（Polygon.io/Marketaux）、加密（CryptoPanic）、学术（arXiv）
2. **更新后的RSS源**：澎湃、Amazon、AMD等
3. **Playwright浏览器抓取**：OpenAI、DeepMind、Anthropic等
4. **传统RSS源**：BBC、NYT、TechCrunch等

### 支持的新闻源

- 国际主流媒体（BBC、NYT、Reuters）
- 金融财经（CNBC、Bloomberg、Yahoo Finance）
- 科技新闻（TechCrunch、The Verge、Ars Technica）
- 加密货币（CoinDesk、Cointelegraph）
- AI研究（OpenAI、DeepMind、Anthropic、HuggingFace）
- 中文媒体（澎湃新闻、南华早报、财联社）

## 系统特性

### 增强版采集器

- **Playwright模式**：引入Playwright模式，针对返回403的站点（如Meta, OpenAI, Tesla）改用无头浏览器模拟访问
- **API降级方案**：对金融类和AI论文类源，优先调用API接口
- **异常处理机制**：如果SSL验证失败，尝试在安全范围内降级验证或通过代理重试
- **更新失效URL库**：根据最新地址列表替换旧的RSS链接

### 智能分析框架

AI分析按照以下结构输出：

- 情绪分
- 核心事实
- 幕后真相
- 对中国影响
- 股市影响
- 操作建议

### 错误处理

- 自动重试机制
- SSL验证降级
- 403/404错误处理
- 网络超时处理

## 配置说明

### 环境变量配置

创建 `.env` 文件，配置以下环境变量：

```env
# DeepSeek API密钥
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 飞书webhook URL
FEISHU_WEBHOOK_URL=your_feishu_webhook_url_here

# 可选：金融API密钥
MARKETAUX_API_KEY=your_marketaux_api_key_here
POLYGON_API_KEY=your_polygon_api_key_here
```

## 使用方法

### 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium  # 安装Playwright浏览器
```

### 直接运行

```bash
python daily_news_bot.py
```

### 使用启动脚本

Windows:
```bash
start_news_bot.bat
```

## 部署建议

### 定时任务

可配合cron或Windows任务计划程序设置定时运行。

### 云服务部署

- 支持在GitHub Actions中运行
- 可部署到各种云服务平台
- 支持Docker容器化部署

## 安全考虑

- 敏感信息通过环境变量配置
- 不在代码中硬编码API密钥
- 支持代理访问（可选）
- SSL证书验证（可配置）

## 许可证

MIT License

## 维护者

Python高级工程师