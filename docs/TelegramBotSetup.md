If you DONT already have a telegram notifications setup please follow the guide to setting that up first
https://medium.com/coinmonks/pycryptobot-with-telegram-83eed5f230c2

Once that is complete and working the following steps will get the Telegram Bot control working

1, install requirements (python3 -m pip install -r requirements.txt -U), if this is a new install/setup then you have probably already done this so can be skipped

2, add "telegrambotcontrol" : 1 to config file

3, add "user_id":  "xxxxxx" to telegram section of config (this is your telegram userid message @myidbot if unsure)

4, add "datafolder": "" to telegram section of config, if running multiple bots in different folders set a shared folder path for them all to access otherwise leave empty or remove from config

5, start self.telegram_bot.py (specify config if not default) this only needs to be started once for which ever bot folder you want

6, goto your telegram bot type /help if you get a response it's working

7, type /setcommands this will setup the commands in an easy access list