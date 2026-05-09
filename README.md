# Daily News Bot

每日投资雷达：从公开新闻、市场价格、行业配置、提醒记忆和操作回执里整理一份中长期投资观察报告。

它不是交易指令系统，也不保证收益。系统的作用是把信息、价格确认、风险闸门、组合纪律和事后复盘放到同一个页面，减少因为单日新闻冲动交易。

## 当前能力

- 多源新闻抓取：RSS、API、官方网页。
- 事件聚合：把重复报道合并成核心事件。
- 中文摘要：外文新闻优先转成中文，飞书卡片隐藏长英文。
- 市场快照：原油、黄金、美元、利率、美股期货等价格确认。
- Dashboard：生成 `outputs/dashboard.html`，GitHub Pages 可展示最新页和历史归档。
- 飞书推送：每天只推中文重点、市场涨跌、关注项、调仓倾向和网页入口。
- 操作回执：有交易时在飞书群里回一行“买入/卖出/加仓/减仓”，系统下次运行会入账；没操作不用回复。
- 中长期周报：默认不每天催买卖，周报入口复核“本周是否需要动作”。
- 行业雷达：跟踪 AI、黄金、半导体材料、能源电力、关键矿产、反内卷、算电协同等主线。
- 30/60/90 天验算：记录建议后续表现，用样本校准权重。
- 错误复盘库：把误判归因到新闻误判、价格没确认、追高、仓位太重、行业逻辑不成立等类别。
- 宏观爆破风险：观察政策换挡、油价、美元、VIX、黄金和高估值资产是否共振；只做风险闸门，不自动买卖。

## 正式入口

本地运行：

```powershell
python daily_news_bot.py --mode evening --hours 24 --top 8
```

测试：

```powershell
python -m unittest discover -s tests
```

GitHub Actions：

- 工作流：`.github/workflows/daily_news.yml`
- 每次运行会生成 `outputs/report.md`、`outputs/report.json`、`outputs/dashboard.html`、`outputs/watchlist.json`、`outputs/signal_validation.json`
- GitHub Pages 使用 Actions 作为发布源，最新 Dashboard 在站点根目录，历史运行在 `runs/`

## 重要目录

```text
.github/workflows/        GitHub Actions 自动运行和发布
config/                   新闻源、提醒、示例组合和示例交易账本
src/daily_news_bot/       正式系统代码
tests/                    单元测试
workers/                  Cloudflare Worker，用于飞书操作回执
daily_news_bot.py         正式命令行入口
```

## 私密配置

不要把真实持仓、飞书密钥、Webhook、App Secret、Cloudflare Token 写进仓库。

本地私密文件默认被 `.gitignore` 忽略：

- `.env`
- `config/portfolio.yaml`
- `config/trade_ledger.yaml`
- Cloudflare 本地 Wrangler 配置

线上用 GitHub Actions Secrets 保存密钥。

## 使用边界

- 不预测保证收益。
- 不自动替你买卖。
- 不把单一新闻直接升级成操作。
- 没有价格、政策、订单或相对强弱确认时，只进入观察。
- 组合建议需要你的真实持仓、成本、目标仓位和飞书回执共同校准。

