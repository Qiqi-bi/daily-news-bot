# 设置飞书机器人环境变量
$env:LARK_APP_ID=$env:LARK_APP_ID
$env:LARK_APP_SECRET=$env:LARK_APP_SECRET
$env:LARK_CHAT_ID=$env:LARK_CHAT_ID

# 运行AI新闻机器人
Write-Host "正在启动AI新闻机器人..." -ForegroundColor Green
python daily_news_bot.py