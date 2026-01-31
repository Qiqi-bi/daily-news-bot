# 🚀 每日AI新闻机器人 - 快速开始

## 项目简介
这是一个基于DeepSeek大模型的智能新闻分析机器人，能够自动抓取全球新闻、进行深度分析，并将结果发送到飞书。

## 📋 快速配置步骤

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置API密钥
在系统环境变量中设置：
- `DEEPSEEK_API_KEY`: DeepSeek API密钥
- `LARK_APP_ID`: 飞书应用ID
- `LARK_APP_SECRET`: 飞书应用密钥
- `LARK_CHAT_ID`: 飞书群聊ID（可选）
- `LARK_USER_ID`: 飞书用户ID（可选）

### 3. 运行机器人
```bash
# 直接运行
python daily_news_bot.py

# 或使用自动安装脚本
python setup_and_run.py
```

## 🕐 一日三报时间安排

机器人会根据当前时间自动判断发送哪种类型的报告：
- **早报**: 北京时间 8:00 (UTC 00:00) - 关注美股收盘、昨夜欧美大事
- **午报**: 北京时间 13:00 (UTC 05:00) - 关注A股/港股午间动态、亚太地缘
- **晚报**: 北京时间 21:00 (UTC 13:00) - 关注欧股开盘、美股盘前动态
- **日终汇总**: 北京时间 00:00 (UTC 16:00) - 全天总结和明日前瞻

## 📁 重要文件说明

- `daily_news_bot.py` - 核心程序文件
- `requirements.txt` - 项目依赖
- `.github/workflows/daily_news.yml` - GitHub Actions自动运行配置
- `LARK_CONFIG.md` - 飞书机器人配置指南
- `FINAL_SUMMARY.md` - 详细项目说明

## 🔧 常见问题

### Q: 如何在GitHub上设置自动运行？
A: 配置好仓库的Secrets（环境变量），然后启用Actions即可。

### Q: 机器人支持哪些新闻源？
A: 支持10个国际主流RSS源，包括BBC、纽约时报、CNBC、TechCrunch等。

### Q: 如何自定义推送时间？
A: 修改 `.github/workflows/daily_news.yml` 文件中的cron表达式。

## 🎯 功能特色

- ✅ 智能新闻抓取与去重
- ✅ AI深度分析与情绪评分
- ✅ 实时资产价格注入
- ✅ 飞书应用认证推送
- ✅ 支持图片和表格格式
- ✅ 一日三报策略
- ✅ 错误监控与警报

## 📞 技术支持

如需帮助，请参考：
- `LARK_CONFIG.md` - 飞书配置说明
- `FINAL_SUMMARY.md` - 详细功能说明
- `README.md` - 项目介绍

---

*祝您使用愉快！🎉*