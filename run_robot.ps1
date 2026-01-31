# 设置飞书机器人环境变量
$env:LARK_APP_ID="cli_a9f6280dd5389bd8"
$env:LARK_APP_SECRET="VHN4Eag0koh7rwEkKXeHSgHzLnH1140x"
$env:LARK_CHAT_ID="oc_efc1ffb36158b2254f263e20b1fef768"

# 运行AI新闻机器人
Write-Host "正在启动AI新闻机器人..." -ForegroundColor Green
python daily_news_bot.py