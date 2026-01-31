@echo off
REM 设置飞书机器人环境变量
set LARK_APP_ID=%LARK_APP_ID%
set LARK_APP_SECRET=%LARK_APP_SECRET%
set LARK_CHAT_ID=%LARK_CHAT_ID%

REM 运行AI新闻机器人
echo 正在启动AI新闻机器人...
python daily_news_bot.py

pause
