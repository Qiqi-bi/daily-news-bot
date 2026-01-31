# 🌟 每日AI新闻机器人 - 项目总结

## 项目概述
这是一个基于DeepSeek大模型的智能新闻分析机器人，能够自动抓取全球新闻、进行深度分析，并将结果发送到飞书。

## ✨ 核心功能

### 1. 新闻抓取
- 从10个国际主流RSS源抓取新闻
- 智能去重和过滤
- 支持图片提取

### 2. AI深度分析
- 使用DeepSeek大模型进行专业分析
- 计算市场情绪指数（-10到+10）
- 注入实时资产价格信息
- 智能分类（必选/必杀）

### 3. 智能推送
- 飞书应用认证
- 支持图片和表格格式
- 一日三报策略（早报/午报/晚报）
- 错误监控和警报

## 📋 主要文件

### 核心代码
- `daily_news_bot.py` - 主程序，包含完整的新闻分析和推送功能
- `requirements.txt` - 项目依赖

### 配置文件
- `.github/workflows/daily_news.yml` - GitHub Actions配置，实现一日三报
- `LARK_CONFIG.md` - 飞书机器人配置说明

### 测试文件
- `test_basic.py`, `test_format.py` - 功能测试脚本
- `setup_and_run.py` - 自动安装和运行脚本

## 🔧 配置说明

### 环境变量
```bash
# DeepSeek API
DEEPSEEK_API_KEY=

# 飞书应用配置
LARK_APP_ID=
LARK_APP_SECRET=
LARK_CHAT_ID=  # 可选
LARK_USER_ID=  # 可选
```

### RSS源列表
- BBC World News
- New York Times
- CNBC Finance
- TechCrunch
- Yahoo Finance
- CoinDesk
- OilPrice.com
- Hacker News
- Reddit WorldNews
- South China Morning Post
- ArXiv AI Papers

## 📅 一日三报时间表

- **早报 (00:00 UTC / 08:00 Beijing)** - 关注美股收盘、昨夜欧美大事
- **午报 (05:00 UTC / 13:00 Beijing)** - 关注A股/港股午间动态、亚太地缘
- **晚报 (13:00 UTC / 21:00 Beijing)** - 关注欧股开盘、美股盘前动态
- **日终汇总 (16:00 UTC / 00:00 Beijing)** - 全天总结和明日前瞻

## 🚀 运行方式

### 本地运行
```bash
# 直接运行
python daily_news_bot.py

# 使用自动安装脚本
python setup_and_run.py

# 使用批处理文件
./run_news_bot.bat
```

### GitHub Actions部署
配置好环境变量后，机器人将在设定时间自动运行。

## 📊 分析特色

### 情绪评分系统
- 🔥+8: 极度利好
- ❄️-8: 极度利空
- ⚡0: 中性事件

### 价格注入功能
自动检测新闻中的资产名称并注入实时价格：
- Bitcoin (BTC)
- Ethereum (ETH)
- Gold (黄金)
- NVIDIA (NVDA)
- Apple (AAPL)
- S&P 500

### 智能分类
- **必选**: 涉及中国、全球地缘政治、重大金融动向、硬核科技
- **必杀**: 体育、娱乐、纯地方性社会新闻

## 🛠 技术特点

1. **智能代理**: 根据环境自动选择是否使用代理
2. **缓存机制**: 避免重复推送相同新闻
3. **重试机制**: 确保API调用稳定性
4. **错误处理**: 完善的异常捕获和警报机制
5. **时间感知**: 根据时间段调整RSS源和分析重点

## 📈 未来扩展

- 数据库集成存储历史分析
- Web界面查看历史报告
- 更多资产价格监控
- 多语言支持

## 📞 故障排除

如果遇到问题，请检查：
1. API密钥是否正确配置
2. 飞书应用权限是否正确设置
3. 网络连接是否正常
4. 环境变量是否正确设置

---
*项目完成日期: 2026年1月30日*
*DeepSeek-V3 智能分析系统*