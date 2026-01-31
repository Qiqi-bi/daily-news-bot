@echo off
REM 设置飞书机器人环境变量
set LARK_APP_ID=cli_a9f6280dd5389bd8
set LARK_APP_SECRET=VHN4Eag0koh7rwEkKXeHSgHzLnH1140x
set LARK_CHAT_ID=oc_efc1ffb36158b2254f263e20b1fef768

REM 运行AI新闻机器人
echo 正在启动AI新闻机器人...
python daily_news_bot.py

pause