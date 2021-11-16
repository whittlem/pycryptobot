Scanning the market

Pycryptobot users frequently ask on the community telegram "how do you choose the markets/pairs?" This market selection is an important decision that should be done with some research and not be left to luck.

The telegram bot control introduces access to a new scanner that eases that painful job of searching in hundreds of markets based on arbitrary user selection. 

For a more detailed explanation of how the scanner functions please read the following

https://playful-curio-e62.notion.site/Scanning-the-market-fd9b58b059dd4cf8addb167af7f36311

If you have not already setup the Telegram Bot you will need it setup to use this function, please checkout the TelegramBot.md for setup instructions

There is a new section added to the config file (this can be found in the config.json.sample).  The section looks like this:

"scanner" : {
	"atr72_pcnt" : 1.0, - the percent value cut off for minimum volatility indicator, tweak this to your preference
	"enableexitaftersell" : 1, - 1/0 exits the bot once does the trade, freeing resources for new markets
	"enableleverage" : 0, - 1/0 allow coins with UP or DOWN prefix/suffixes.
	"maxbotcount" : 5, - number of maximum bots running concurrently (not including an with open orders).
    "autoscandelay" : 0 - number of hours between auto scans, 0 is non scheduled.
	"enable_buy_next": 1 - 1/0 enable/disable buy_next from scanner output, this taken from EMA(ema12ltema26), if disabled buy_next will be ignored
}

If you already have the Telegram Bot running you will need to run /setcommands to pull in the latest commands, this will give you the following commands:

/startscanner - this will start the scanner and process and create a schedule if configured
/stopscanner - if a schedule has been created this will remove it 
/addexception - add a pair to the exception list, a pair on the exception list will not start if it is picked up as part of the scanning process (can be useful for HODL pairs)
/removeexception - this will remove a pair from the exceptions list

The scanning process can take a little bit of time and while that is processing "Gathering data.." your Telegram Bot won't respond to any other commands until it is complete, once the scanning process has complete any running bots that don't have an open order will be stopped and you will start to get notifications as the Telegram Bot begins to start-up bots.

*This is no guarantee of profits just an indication of pairs likely to be on an uptrend


