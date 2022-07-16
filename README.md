# Python Crypto Bot v6.4.3 (pycryptobot)

[![Docker](https://github.com/whittlem/pycryptobot/actions/workflows/container.yml/badge.svg)](https://github.com/whittlem/pycryptobot/actions/workflows/container.yml/badge.svg) [![Tests](https://github.com/whittlem/pycryptobot/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/whittlem/pycryptobot/actions/workflows/unit-tests.yml/badge.svg)

## Join our chat on Telegram

<https://t.me/joinchat/09hYKfelbRY2MDNk>

## Supporting The Project

I get paid to write on Medium. Readers following me, applauding and commenting on my articles, all helps with my earnings. I provided this bot to all of you for free and actively developing it. One way you can support my efforts is to follow me on Medium and read my articles. The Medium subscription is $5 a month (roughly £3) so basically nothing in terms of the value you are getting from the bot. Your efforts here would be greatly appreciated!

Follow me on Medium for updates!

<https://whittle.medium.com>

Python Crypto Bot (PyCryptoBot)

<https://medium.com/coinmonks/python-crypto-bot-pycryptobot-b54f4b3dbb75>

What’s new in PyCryptoBot 2?

<https://medium.com/coinmonks/whats-new-in-pycryptobot-2-a4bbb1b0c90e>

PyCryptoBot with Telegram

<https://medium.com/coinmonks/pycryptobot-with-telegram-83eed5f230c2>

PyCryptoBot Results and Config

<https://medium.com/coinmonks/pycryptobot-results-and-config-57fb6625a6d9>

Coinbase Pro Portfolio Tracker

<https://medium.com/coinmonks/coinbase-pro-portfolio-tracker-a6e4a1c6b8f8>

TradingView.com Charts ❤

<https://levelup.gitconnected.com/tradingview-com-charts-36a49c9f77ea>

## Optional Add-on

Coinbase Pro Portfolio Tracker

<https://github.com/whittlem/coinbaseprotracker>

An all-in-one view of all your Coinbase Pro portfolios. Highly recommended
if running multiple bots and keeping track of their progress.

## Prerequisites

* When running in containers: a working docker/podman installation

* Python 3.9.x installed -- <https://installpython3.com>  (must be Python 3.9 or greater)

    % python3 --version

    Python 3.9.1

* Python 3 PIP installed -- <https://pip.pypa.io/en/stable/installing>

    % python3 -m pip --version

    pip 21.0.1 from /usr/local/lib/python3.9/site-packages/pip (python 3.9)

## Installation

### Manual

    % git clone https://github.com/whittlem/pycryptobot
    % cd pycryptobot
    % python3 -m pip install -r requirements.txt

### Container

    Install Docker Desktop
    https://docs.docker.com/desktop

From Github image repo

    % docker pull ghcr.io/whittlem/pycryptobot/pycryptobot:latest
    latest: Pulling from whittlem/pycryptobot/pycryptobot
    8f403cb21126: Pull complete
    65c0f2178ac8: Pull complete
    1091bd628216: Pull complete
    cb1eb04426a4: Pull complete
    ec065b94ad1c: Pull complete
    Digest: sha256:031fd6c7b7b2d08a743127e5850bc3d9c97a46e02ed0878f4445012eaf0619d3
    Status: Downloaded newer image for ghcr.io/whittlem/pycryptobot/pycryptobot:latest
    ghcr.io/whittlem/pycryptobot/pycryptobot:latest

Local repo

    % docker build -t pycryptobot .

## Additional Information

The "requirements.txt" was created with `python3 -m pip freeze`

## Run it

### Manual

    % python3 pycryptobot.py <arguments>

### Docker (Option 1)

    Example Local Absolute Path: /home/example/config.json
    Example Market: BTC-GBP

    Daemon:
    % docker run --name BTC-GBP -v /home/example/config.json:/app/config.json -d ghcr.io/whittlem/pycryptobot/pycryptobot:latest <arguments>

    Example:
    % docker run --name BTC-GBP -v /Users/whittlem/Documents/Repos/Docker/config.json:/app/config.json -d ghcr.io/whittlem/pycryptobot/pycryptobot:latest --live 0
    e491ae4fdba28aa9e74802895adf5e856006c3c63cf854c657482a6562a1e15

    Interactive:
    % docker run --name BTC-GBP -v /home/example/config.json:/app/config.json -it ghcr.io/whittlem/pycryptobot/pycryptobot:latest <arguments>

    List Processes:
    % docker ps

    Example:
    % docker ps
    CONTAINER ID   IMAGE                                             COMMAND                  CREATED          STATUS          PORTS     NAMES
    e491ae4fdba2   ghcr.io/whittlem/pycryptobot/pycryptobot:latest   "python3 pycryptobot…"   46 seconds ago   Up 44 seconds             BTC-GBP

    Container Shell:
    % docker exec -it BTC-GBP /bin/bash
    [root@e491ae4fdba2 app]#

    Build your own image (if necessary):
    docker build -t pycryptobot_BTC-GBP .

    Running the docker image:
    docker run -d --rm --name pycryptobot_BTC-GBP_container pycryptobot_BTC-GBP

Typically I would save all my settings in the config.json but running from the command line I would usually run it like this.

    % python3 pycryptobot.py --market BTC-GBP --granularity 3600 --live 1 --verbose 0 --selllowerpcnt -2

### docker-compose (Option 2)

To run using the config.json in template folder,

    % docker-compose up -d

By default, docker-compose will use the config inside `./market/template`. We provide this as a template for any market config.

For each market you want to trade, create a copy of this folder under market.
Also create either a coinbase.key or binance.key file to each folder depending which trading platform is being used.
For example, if you are trading `BTCEUR` and `ETHEUR` your market folder should look like this:

    ├── market
    │ ├── BTCEUR
    │ │ ├── config.json
    │ │ ├── pycryptobot.log
    │ │ └── graphs
    │ └── ETHEUR
    │   ├── config.json
    │   ├── pycryptobot.log
    │   └── graphs

modify docker-compose.yaml

    version: "3.9"

    services:
      btceur:
        build:
          context: .
        container_name: btceur
        volumes:
          - ./market/BTCEUR/coinbase.key:/app/coinbase.key.json
          - ./market/BTCEUR/config.json:/app/config.json
          - ./market/BTCEUR/pycryptobot.log:/app/pycryptobot.log
          - ./market/BTCEUR/graphs:/app/graphs
          - /etc/localtime:/etc/localtime:ro
        environment:
          - PYTHONUNBUFFERED=1
        deploy:
          restart_policy:
            condition: on-failure

      etheur:
        build:
          context: .
        container_name: etheur
        volumes:
          - ./market/ETHEUR/coinbase.key:/app/coinbase.key.json
          - ./market/ETHEUR/config.json:/app/config.json
          - ./market/ETHEUR/pycryptobot.log:/app/pycryptobot.log
          - ./market/ETHEUR/graphs:/app/graphs
          - /etc/localtime:/etc/localtime:ro
        environment:
          - PYTHONUNBUFFERED=1
        deploy:
          restart_policy:
            condition: on-failure

Run all your bots. Note that each market should have it's own config. Graphs will be saved on each market's folder.

    % docker-compose up -d

### Kubernetes (Helm) (Option 3)

There is a helm chart available in this repo. It will create your config.json as a configmap and the binance/coinbase keys as secrets, and mount them into the Pod.
To run pycryptobot as a Kubernetes deployment, create your helm values as yaml in the following format (do not change the path to the api_key_file):

    config: >
        {
            "coinbasepro": {
                "api_url": "https://api.pro.coinbase.com",
                "config": {
                    "base_currency": "ETH",
                    "quote_currency": "EUR",
                    "live": 1,
                    "sellatloss": 0,
                    "disablelog": 1,
                    "autorestart": 1
                },
                "api_key_file": "/app/keys/coinbasepro.key"
            },
            "telegram" : {
                "token" : "<telegram_token>",
                "client_id" : "<client_id>",
            }
        }

    coinbasepro_key: |
        XXXXXXXXXXXXXXXXXXXX
        YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
        zzzzzzzzzzzz

Or, for binance:

    config: >
        {
            "binance": {
                "api_url": "https://api.binance.com",
                "config": {
                    "base_currency": "ETH",
                    "quote_currency": "EUR",
                    "live": 1,
                    "sellatloss": 0,
                    "disablelog": 1,
                    "autorestart": 1
                },
                "api_key_file": "/app/keys/binance.key"
            },
            "telegram" : {
                "token" : "<telegram_token>",
                "client_id" : "<client_id>",
            }
        }

    binance_key: |
        XXXXXXXXXXXXXXXXXXXX
        YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY

Or, for kucoin:

    config: >
        {
            "kucoin": {
                "api_url": "https://api.kucoin.com",
                "config": {
                    "base_currency": "ETH",
                    "quote_currency": "EUR",
                    "live": 1,
                    "sellatloss": 0,
                    "disablelog": 1,
                    "autorestart": 1
                },
                "api_key_file": "/app/keys/coinbasepro.key"
            },
            "telegram" : {
                "token" : "<telegram_token>",
                "client_id" : "<client_id>",
            }
        }

    kucoin_key: |
        XXXXXXXXXXXXXXXXXXXX
        YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
        zzzzzzzzzzzz

Or both:

    config: >
        {
            "coinbasepro": {
                "api_url": "https://api.pro.coinbase.com",
                "config": {
                    "base_currency": "ETH",
                    "quote_currency": "EUR",
                    "live": 1,
                    "sellatloss": 0,
                    "disablelog": 1,
                    "autorestart": 1
                },
                "api_key_file": "/app/keys/coinbasepro.key"
            },
            "binance": {
                "api_url": "https://api.binance.com",
                "config": {
                    "base_currency": "ETH",
                    "quote_currency": "EUR",
                    "live": 1,
                    "sellatloss": 0,
                    "disablelog": 1,
                    "autorestart": 1
                },
                "api_key_file": "/app/keys/binance.key"
            },
            "kucoin": {
                "api_url": "https://api.kucoin.com",
                "config": {
                    "base_currency": "ETH",
                    "quote_currency": "EUR",
                    "live": 1,
                    "sellatloss": 0,
                    "disablelog": 1,
                    "autorestart": 1
                },
                "api_key_file": "/app/keys/kucoin.key"
            },
            "telegram" : {
                "token" : "<telegram_token>",
                "client_id" : "<client_id>",
            }
        }

    coinbasepro_key: |
        XXXXXXXXXXXXXXXXXXXX
        YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
        zzzzzzzzzzzz
    binance_key: |
        XXXXXXXXXXXXXXXXXXXX
        YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
    kucoin_key: |
        XXXXXXXXXXXXXXXXXXXX
        YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
        zzzzzzzzzzzz

Then run:

    git clone https://github.com/whittlem/pycryptobot
    cd pycryptobot/chart
    helm upgrade -i pycryptobot-eth-eur -f <path_to_helm_config>

So if you created above helm values file as config-eth-eur.yaml, you would run:

    helm upgrade -i pycryptobot-eth-eur -f config-eth-eur.yaml

## Bot mechanics

Smart switching:

* If the EMA12 is greater than the EMA26 on the 1 hour and 6 hour intervals switch to start trading on the 15 minute intervals
* If the EMA12 is lower than the EMA26 on the 1 hour and 6 hour intervals switch back to trade on the 1 hour intervals
* If a "granularity" is specified as an argument or in the config.json then smart switching will be disabled
* Force smart switching between 1 hour and 15 minute intervals with "smartswitch" argument or config option (1 or 0)

Buy signal:

* EMA12 is currently crossing above the EMA26 and MACD is above the Signal *OR* MACD is currently crossing above the Signal and EMA12 is above the EMA26
* Golden Cross (SMA50 is above the SMA200) <-- bull market detection
* On-Balance Volume Percent > -5 <-- suitable momentum required
* Elder Ray Buy is True <-- bull market detection

The bot will only trade in a bull market to minimise losses! (you can disable this)

Special buy cases:

* "nobuynearhighpcnt" to specify the percentage from high that the bot should not buy if "disablebuynearhigh" is not specified.
* "buymaxsize" specifies a fixed max amount of the quote currency to buy with.
* "buylastsellsize" when enabled, bot will buy the same size as the last sell size for the current market.
* "trailingbuypcnt" specifies the percentage for the self.price to increase before placing buy order after receiving buy signal. Eg: 0.5   (must be positive integer)
Note: the trailingbuy function will buy if the self.price is within 10% of the trailingbuypcnt setting.
* "trailingbuyimmediatepcnt" is a separate setting for percentage of self.price increase that can be used with "trailingimmediatebuy" or with the new Custom Strategies. (see separate explanation)
     Eg: 1.5   (must be positive integer)
* "trailingimmediatebuy" (0 to disable, 1 to enable, disabled by default) will trigger an immediate buy if "trailingbuyimmediatepcnt" is reached.  Use caution, may not advisable on all markets. Without "trailingimmediatebuy", default is to wait until candle close to process buy like a standard buy signal. (As of v6.3.0, "trailingbuyimmediatepcnt" is required for an immediate buy.)
* "marketmultibuycheck" when enabled, bot will perform an additional check on base and quote balance to prevent multiple buys.
        It has been determined that some market pairs have problem API responses which can create a multiple buy issue.
        Please Note:  "marketmultibuycheck" will conflict with configurations that use "sellpercent".

Sell signal:

* EMA12 is currently crossing below the EMA26
* MACD is below the Signal

Special sell cases:

* "no_sell_min_pcnt" specifies the lower margin limit to not sell above
* "no_sell_max_pcnt" specifies the upper margin limit to not sell below
* If "sellatloss" is on, bot will sell if self.price drops below the lower Fibonacci band
* If "sellatloss" is on and "selllowerpcnt" is specified the bot will sell at the specified amount E.g. -2 for -2% margin
* If "sellatloss" is on and "trailingstoploss" is specified the bot will sell at the specified amount below the buy high
* If "sellupperpcnt" is specified the bot will sell at the specified amount E.g. 10 for 10% margin (Depending on the conditions I lock in profit at 3%)
* If the margin exceeds 3% and the self.price reaches a Fibonacci band it will sell to lock in profit
* If the margin exceeds 3% but a strong reversal is detected with negative OBV and MACD < Signal it will sell
* "sellatloss" set to 0 prevents selling at a loss
* "preventloss" set to 1 to force a sell before margin is negative (losing money on active trade).  Default trigger point is 1%.  If no_sell_max_pcnt is set it will be used as the default, unless preventlosstrigger is set to set a custom trigger point.
* "preventlosstrigger" is the margin set point that will trigger/allow the preventloss function to start watching the margin and will sell when margin reaches 0.1% or lower unless preventlossmargin is set.
    NOTE: to disable preventlosstrigger and use preventlossmargin only, set the trigger to 0.
* "preventlossmargin" is the margin set point that will cause an immediate sell to prevent a loss.  If this is not set, a default of 0.1% will be used.  "preventlossmargin" can be used by itself or in conjunction with "preventlosstrigger".
* "trailingsellpcnt" specifies the percentage for the self.price to decrease before placing sell order after receiving sell signal.  Eg: -0.5   (must be negative integer)
Note: the trailingsell function will sell if the self.price is within 10% of the trailingsellpcnt setting.
* "trailingsellimmediatepcnt" is a separate setting for percentage of self.price decrease that can be used with "trailingimmediatesell" or with the new Custom Strategies. (see separate explanation)   Eg: -1.5   (must be negative integer)
* "trailingimmediatesell" (0 to disable, 1 to enable, disabled by default) will trigger an immediate sell if "trailingsellimmediatepcnt" is reached.  Use caution, may not advisable on all markets. Without "trailingimmediatesell", default is to wait until candle close to process sell like a standard sell signal.
* "trailingsellbailoutpcnt" is a setting that is used with trailing sell and works like "trailingimmediatesell" or like "selllowerpcnt".  This is the percentage of decrease when you absolutely want to sell right away or "bailout" of the trade.  Regardless of other trailing sell settings or anything in Custom Strategies, this is the set point that if the self.price is dropping like a rock, you want to "bailout" NOW because you definitely don't want to wait until candle close or you're going to lose funds.   Eg: -3.0   (must be negative integer)
* "dynamictsl" (Dynamic Trailing Stop Loss) when enabled, with the additional required settings, works like the default trailingstoploss, but dynamically increases both the trigger margin and the stoploss percentage. Set to 1 to enabled and it's disabled by default.  To use the original, static trailingstoploss, just use "trailingstoploss" and "trailingstoplosstrigger"
* "tslmultiplier" this is a positive integer (eg. 1.5) that is multiplied by "trailingstoploss" when "trailingstoplosstrigger" is reached to set the next "trailingstoploss" level.
* "tsltriggermultiplier" is a positive integer (eg. 1.5) that is multiplied by "trailingstoplosstrigger" when the previous trigger settings is reach to set the next "trailingstoplosstrigger" level.
    NOTE: both "trailingstoploss" and "trailingstoplosstrigger" settings are still required WITH "dynamictsl" as well as "tslmultipler", "tsltriggermultiplier" and "tslmaxpcnt" are also required.
* "adjust_total_periods" is an integer > 26 and < 300 used to adjust the total periods (candles) in the current dataframe for the current market used in technical analysis.  This setting came about because Kucoin made changes to their API that is currently only returning 100 periods (candles) for responses.  Hopefully this problem will be resolved, but adjusting the total periods can be useful when trying to trade new crypto pairs that don't have a full 300 periods of data yet.
    *** Note:  if adjusting to less than 300 periods, Trading Graphs, SMA Buy Signals and "disablebullonly" will NOT work correctly as well as some of the other indicators.  Only use this setting if absolutely necessary or you know what you are doing.  Pycryptobot is designed to analyze 300 candles for each market.

## Optional Options

    --stats                             Display order profit and loss (P&L) report
    --autorestart                       Automatically restart the bot on error
    --sellatresistance                  Sells if the self.price reaches either resistance or Fibonacci band
    --enable_telegram_bot_control          Enable bot control via Telegram
    --sellsmartswitch                   Enables smart switching to 5 minute granularity after a buy is placed
    --enableinsufficientfundslogging    Stop insufficient fund errors from stopping the bot, instead log and continue
    --manual_trades_only                Enable Manual Trading Only for pairs you want to HODL and you don't want to trade automatically

## Disabling Default Functionality

    --disablebullonly                   Disable only buying in bull market
    --disablebuynearhigh                Disable buying within 3% of the dataframe high
    --disablebuymacd                    Disable macd buy signal
    --disablebuyema                     Disable ema buy signal.If both core indicators ema and macd buy signals are disabled, bot won't buy.Doesn't affect sell strategy.
    --disablebuyobv                     Disable obv buy signal
    --disablebuyelderray                Disable elder ray buy signal
    --disablefailsafefibonaccilow       Disable failsafe sell on fibonacci lower band
    --disablefailsafelowerpcnt          Disable failsafe sell on 'selllowerpcnt'
    --disableprofitbankupperpcnt        Disable profit bank on 'sellupperpcnt'
    --disableprofitbankfibonaccihigh    Disable profit bank on fibonacci upper band
    --disableprofitbankreversal         Disable profit bank on strong candlestick reversal
    --disabletelegram                   Disable sending telegram messages
    --disable_telegram_error_msgs          Disable sending error message to telegram (only trading info)
    --telegramtradesonly                Toggle only sending trade messages to telegram - won't send smart switch and last action messages, will still send error messages unless disabling separately
    --disablelog                        Disable writing log entries
    --disabletracker                    Disable saving CSV on buy and sell events

## "Sell At Loss" explained

The "sellatloss" option disabled has it's advantages and disadvantages. It does prevent any losses but also prevents you from exiting a market before a crash or bear market. Sometimes it's better to make an occasional small loss and make it up with several buys than be conservative and potentially lock a trade for weeks if not months. It happened to me while testing this with the last crash (after Elon's tweet!). Three of my bots did not sell while the profit dropped to -10 to -20%. It did bounce back and I made over 3% a trade with any losses but I also lost out of loads of trading opportunities. It's really a matter of preference. Maybe some markets would be more appropriate than others for this.

## "Prevent Loss" explained

The "preventloss" option and it's corresponding settings add more options to control losses or minimize losses on trades.  "preventloss" does not depend on "sellatloss" to work.  The idea of Prevent Loss is to allow you to still use all the other sell criteria and the no sell zones as you would like, but still sell prior to the margin dropping below 0%.  Note: there are still transaction fees from the exchange, this has no effect on fees.  You could increase preventlossmargin to account for fees if you would like.
If "preventloss" is set to 1 and enabled, it will watch for the "preventlosstrigger" margin percentage to be reached. If "preventloss" is enabled and "preventlosstrigger" is NOT in you configuration the default "preventlosstrigger" is 1%.  Once the trigger percentage is reached, preventloss will monitor the margin until it falls to the "preventlossmargin" set point.  If "preventlossmargin" is not in your configuration, it has a default setting of 0.1% to make the best attempt to trigger a sell before the margin drops below 0%.  On very fast falling self.prices, the margin could fall below 0% before the transaction is processed by the exchange.  Set at a level that you are comfortable with so the margin falls in the range you would like.

"preventloss" and "preventlossmargin" can be used without "preventlosstrigger" if you choose.  Set "preventlosstrigger" to 0 in your config to disable it and sell any time the margin drops below the "preventlosmargin" set point.  It is assumed that most users won't want this option which is why you have to disable "preventlosstrigger" for it to function in this manner.

Prevent Loss is not a required option.  It allows a little more control over your profits and losses.

## Trailing Buy Percent Explained

When the bot issues a standard buy signal via all normal methods, it waits until the next candle close to buy.  Many times after a buy signal is given, the self.price for the pair in question will still fall.  Trailing buy will, by default,  check to make sure the self.price is moving in a positive/upward direction before it buys.  If the self.price goes lower after the buy signal is given, trailing buy will watch the self.price changes and will prevent a buy if the self.price is dropping until it starts to increase again.  This will actually make the bot buy at the lowest self.price monitored after the buy signal was received.  The default is 0% of increase, so it will only prevent buying from the buy signal until next candle close if the self.price is decreasing.  At close, if the self.price is still falling, it will delay the buy again until next close.  This essentially takes an extra step to help stop you from possibly losing profit immediately after a buy, especially when using MACD signals only.
"trailingbuypcnt" can be set at any percentage above 0.  Run some simualutions or use live: 0 to test the results of various percentage set points.  During testing, 1% had pretty good results, but all trade settings will vary based on market and pair being traded.  It is always recommended that you run tests before trading live with real funds.

"trailingimmediatebuy" is another setting that can be used in conjunction with "trailingbuypcnt".  If "trailingimmediatebuy" is enabled (set to 1), "trailingbuypcnt" will buy immediately upon the set point being reached, instead of waiting until candle close.  Again, run tests to determine the best settings.

## Trailing Sell Percent Explained

Trailing Sell is essentially the opposite of Trailing Buy.  It works when a sell signal is received and watches the self.price to make sure it's actually decreasing before selling.  Indicators can trigger a sell signal, but the self.price might only drop -0.25% and then start to rise again.  Rather than selling right away (candle close), the self.price point is recored at time the sell signal is received and monitored for decrease.  When the self.price drops to the "trailingsellpcnt" set point, the trailing sell is triggered and the bot will sell at candle close.  If the self.price increases above the set point, it is reset and starts tracking from there.  This will make sure you get as much profit as possible before selling.  If you watch charts and signals, you should be able to see the benefit to this setting over time.

Additionally "trailingimmediatesell" and "trailingsellimmediatepcnt" are more options that can be used with trailing sell.  Set "trailingsellimmediatepcnt" below "trailingsellpcnt" as an extra level of loss protection.  When the bot issues a sell signal, sometimes the self.price drops slowly, but many time the self.prices drops quickly and this will make sure the sell happens before candle close if the self.price is dropping rapidly.  "trailingimmediatesell" enables this feature and uses "trailingsellimmediatepcnt" as the set point.

Trailing Sell has one additional option, "trailingsellbailoutpcnt". This was added mostly for use with Custom Strategies because "trailingsellimmediatepcnt" is used differently with Custom Strategies, but can be used by itself, instead of requiring both "trailingimmediatesell" settings.  It works the same as "trailingimmediatesell", but only requires a negative percentage to be set with "trailingsellbailoutpcnt".  Think of this as a failsafe.  If by chance you had a buy and your bot is using 1 hour granularity and you get a sell signal just a few minutes after the top of the hour.  The bot will have to wait for candle close at the top of the next hour before it sells.  What if the self.price drops 25% within that hour?  Ouch!  That's a big loss.  Everyone has a different opinion of the set points, but it's not recommended to set this too close to 0.  A setting of -1.5 to -3 would probably be good.

## Dynamic Trailing Stoploss Explained

The default, static trailing stoploss works as follows:  when the margin of the current trade reaches the trailing stoploss trigger set point, the trigger is set and the bot watches for the margin to drop as much as the trailing stoploss setting.  If trigger setting is 5% and trailing stoploss setting is -1.5% and the margin reaches or passes 5%, the trigger is activated.  Now when the margin decreases -1.5% from the trigger point an immediate sell occurs.

With Dynamic Trailing Stoploss, both the trigger and the stoploss settings dynamically increase as the margin continues to increase.  Many times the more the margin increases (symbol self.price increases), you may see bigger drops or dips in the chart as the self.price continues to climb.  By dynamically adjusting, as your margin gets bigger, most people are willing to accept a littel bit bigger loss from the top before selling.  Because everyone has different opinions on what is a reasonable loss, that's why the multipliers are two different settings.

Set the "trailingstoploss" and "trailingstoplosstrigger" starting points. (eg. -1 and 3)  Then enabled "dynamictsl" with a 1.  Add "tslmultiplier" (eg. 1.5) and "tsltriggermultipler" (eg. 1.5) and additionally, add "tslmaxpcnt" (eg. -5).

Your bot does buy, the margin passes the initial trigger of 3%, the trigger is now active and if the self.price decreases -1% from the triggered or next highest margin, the bot will perform an immediate sell.  If the margin continues to increase and passes the initial trigger multipled by "tsltriggermultiplier", the "trailingstoplosstrigger" is increased and "trailingstoploss" is  increased by "tslmultiplier".  Trigger:  3 X 1.5 = 4.5   Stoploss: -1 X 1.5 = -1.5   If the margin continues to increase and passes the next trigger, the process happens again.  There is a limit though, which is what "tslmaxpcnt" is for.  When the result of multiplying "trailingstoploss" by the multiplier is greater than or equal to "tslmaxpcnt", the increases stop and the last trigger and stoploss setting stay set until a sell occurs.

## Live Trading

In order to trade live you need to authenticate with the Coinbase Pro or Binance APIs. This is all documented in my Medium articles. In summary you will need to include a config.json file in your project root which contains your API keys. If the file does not exist it will only work in test/demo mode.

## Trading Simulation

    --sim ['fast, fast-sample, slow-sample']   Sets simulation mode
    --simstart_date                             Start date for sample simulation e.g '2021-01-15'
    --simend_date                               End date for sample simulation or 'now'

`simstart_date` takes priority over `simend_date` if both are given

### Simulation trades.csv

By default, when running a simulation, if there are any orders,  a file called `trades.csv` with all BUYS and SELLS will be created.

With `--tradesfile` you can control the name and where file is stored, eg `--tradesfile BTSUDC-trades.csv`

## API key / secret / password storage

From now on it's recommended NOT to store the credentials in the config file because people share configs and may inadvertently share their API keys within.

Instead, please, create `binance.key` or `coinbase.key` or `kucoin.key` (or use your own names for the files) and refer to these files in the `config.json` file as:

    "api_key_file" : "binance.key"

Once you have done that, "api_key" and "api_secret" can be safely removed from your config file and you're free to share your configs without worrying of leaked credentials.

You may also specify API key file with a command line argument like:

    --api_key_file binance.key

### binance.key / conbase.key / kucoin.key examples

Actually it's pretty simple, these files are supposed to be a simple text files with the API key on the first line, API secret on the second line and in case of coinbase and kucoin, probably the API password on the third. No comments or anything else is allowed, just the long string of numbers:

    0234238792873423...82736827638472
    68473847745876abscd9872...8237642

(dots are used to indicate places where the strings were shortened)

## config.json examples

Coinbase Pro basic (using smart switching)

    {
        "api_url" : "https://api.pro.coinbase.com",
        "api_key_file" : "coinbase.key",
        "config" : {
            "cryptoMarket" : "BTC",
            "fiatMarket" : "GBP",
            "live" : 1,
            "sellatloss" : 0
        }
    }

Coinbase Pro basic (specific granularity, no smart switching)

    {
        "api_url" : "https://api.pro.coinbase.com",
        "api_key_file" : "coinbase.key",
        "config" : {
            "cryptoMarket" : "BCH",
            "fiatMarket" : "GBP",
            "granularity" : 3600,
            "live" : 1,
            "sellatloss" : 0
        }
    }

Coinbase Pro only (new format)

    {
        "coinbasepro" : {
            "api_url" : "https://api.pro.coinbase.com",
            "api_key_file" : "coinbase.key",
            "config" : {
                "base_currency" : "BTC",
                "quote_currency" : "GBP",
                "granularity" : "3600",
                "live" : 0,
                "verbose" : 0
            }
        }
    }

Binance only (new format)

    {
        "binance" : {
            "api_url" : "https://api.binance.com",
            "api_key_file" : "binance.key",
            "config" : {
                "base_currency" : "BTC",
                "quote_currency" : "ZAR",
                "granularity" : "1h",
                "live" : 0,
                "verbose" : 0
            }
        }
    }

Kucoin (using smart switching)

    {
        "api_url" : "https://api.kucoin.com",
        "api_key_file" : "kucoin.key",
        "config" : {
            "base_currency" : "BTC",
            "quote_currency" : "GBP",
            "live" : 1,
            "sellatloss" : 0
        }
    }
Coinbase Pro, Binance and Kucoin (new format)

    {
        "binance" : {
            "api_url" : "https://api.binance.com",
            "api_key_file" : "binance.key",
            "config" : {
                "base_currency" : "BTC",
                "quote_currency" : "ZAR",
                "granularity" : "1h",
                "live" : 0,
                "verbose" : 0
            }
        },
        "coinbasepro" : {
            "api_url" : "https://api.pro.coinbase.com",
            "api_key_file" : "coinbase.key",
            "config" : {
                "base_currency" : "BTC",
                "quote_currency" : "GBP",
                "granularity" : "3600",
                "live" : 0,
                "verbose" : 0
            }
        },
        "kucoin" : {
            "api_url" : "https://api.kucoin.com",
            "api_key_file" : "kucoin.key",
            "config" : {
                "base_currency" : "BTC",
                "quote_currency" : "GBP",
                "granularity" : "3600",
                "live" : 0,
                "verbose" : 0
            }
        }
    }

All the "config" options in the config.json can be passed as arguments E.g. --market <market>

Command line arguments override config.json config.

For telegram, add a piece to the config.json as follows:

    "telegram" : {
        "token" : "<token>",
        "user_Id" : "<user id>"
        "client_id" : "<client id>"
    }

You can use @botfather and @myidbot in telegram to create a bot with token and get a client id.

For configuring the volume scanner, add a piece to the config.json as follows:

    "scanner" : {
		"atr72_pcnt" : <float> # default 2.0,
		"enableexitaftersell" : 1, # once a bot has sold it will exit
		"enableleverage" : 0, # allow leverage markets from the scanner to start
		"maxbotcount" : <int>, # maximum amount of bots you want running at once
		"autoscandelay": <hours>, # number of hours you want to wait between scans
	}

For configuring logger, add a piece to the config.json as follows:
*This is also default configuration of the logger, if no config is given and log is not disabled this configuration will apply.*

    "logger" : {
        "filelog": 1,
        "logfile": "pycryptobot.log",
        "fileloglevel": "DEBUG",
        "consolelog": 1,
        "consoleloglevel": "INFO"
    }

"filelog" and "consolelog" can only get 1 (enable) or 0 (disable).
"--disablelog" argument or "disablelog" config will disable to writing logfile as backwards compatibility.
If you want to disable logging entirely, you can set "filelog" and "consolelog" to 0.

"logfile" is overridden by '--logfile' console argument.
If '--logfile' used when running bot "logfile": "pycryptobot.log" line in config file will be ignored.

"fileloglevel" and "consoleloglevel" can get one of 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'
For further detail in log levels: <https://docs.python.org/3/library/logging.html#logging-levels>

## Multi-Market Trading

The bot can trade multiple markets at once. This is also documented in my Medium articles. The bot will execute buys using the full "quote currency" balance it has access too and it will sell the full "base currency" balance it has access too. In order to ring-fence your non-bot funds you should create another "Portfolio" in Coinbase Pro and assign API keys to it. That way you limit exposure. You can so something similar with Binance using sub-accounts but I believe you need to be a certain level to do this.

The way you trade multiple markets at once is create multiple Coinbase Pro portfolios for each each bot instance. You will then clone this project for additional bots with the relevant Portfolio keys (config.json).

I have 5 bots running at once for my Portfolios: "Bot - BTC-GBP", "Bot - BCH-GBP", "Bot - ETH-GBP", "Bot - LTC-GBP", and "Bot - XLM-EUR".

Assuming each bot has a config.json that looks similar to this (update the "cryptoMarket" and "fiatMarket" appropriately):

    {
        "api_url" : "https://api.pro.coinbase.com",
        "api_key_file" : "coinbase.key"
        "config" : {
            "cryptoMarket" : "BTC",
            "fiatMarket" : "GBP",
            "live" : 1
            "selllowerpcnt" : -2
        }
    }

The way I run my five bots is as follow:

    BTC-GBP % rm pycryptobot.log; git pull; clear; python3 pycryptobot.py

    BCH-GBP % rm pycryptobot.log; git pull; clear; python3 pycryptobot.py

    ETH-GBP % rm pycryptobot.log; git pull; clear; python3 pycryptobot.py

    LTC-GBP % rm pycryptobot.log; git pull; clear; python3 pycryptobot.py

    XLM-EUR % rm pycryptobot.log; git pull; clear; python3 pycryptobot.py

Notice how I don't pass any arguments. It's all retrieved from the config.json but you can pass the arguments manually as well.

## The merge from "binance" branch back into "main"

Some of you may have been helping test the new code for a few months in the "binance" branch. This is now merged back into the "main" branch. If you are still using the "binance" branch please carry out the following steps (per bot instance).

    git reset --hard
    git checkout main
    git pull
    python3 -m pip install -r requirements.txt

Please note you need to be using Python 3.9.x or greater. The previous bot version only required Python 3.x.

## Stats Module

To keep track of the bots performance over time you can run the stats module. e.g.

    python3 pycryptobot.py --stats

This will analyse all the completed buy/sell trade pairs to give stats on todays trades, the trades over the last 7 days, the trades over the last 30 days, and all-time trades.

An optional flag of --statstart_date can be given to ignore all trades that happened before a specified date. The date must be of the format: yyyy-mm-dd. e.g.

    python3 pycryptobot.py --stats --statstart_date 2021-6-01

To get the stats from all your bots, another optional flag of --statgroup can be used. This takes a list of markets and merges the results into one output. e.g.

    python3 pycryptobot.py --stats --statgroup BTCGBP ETHGBP ADAGBP

or via the config.json file e.g.

    "config": {
        ....
        "stats": 1,
        "statgroup": ["BTCGBP", "ETHGBP", "ADAGBP"],
        ....
    }
Note: --statgroup only accepts a group of markets if the quote currency (in this example GBP) is the same.

If you want more detail than the simple summary, add the optional flag --statdetail. This will print a more detailed list of the transactions.
--statdetail can work in conjunction with --statstart_date and --statgroup.

## Upgrading the bots

I push updates regularly and it's best to always be running the latest code. In each bot directory make sure you run this regularly.

    git pull

I've actually included this in the examples in how to start the bot that will do this for you automatically.

## Fun quick non-live demo

    python3 pycryptobot.py --market BTC-GBP --granularity 3600 --sim fast --verbose 0

If you get stuck with anything email me or raise an issue in the repo and I'll help you sort it out. Raising an issue is probably better as the question and response may help others.

Enjoy and happy trading! :)



#### Advanced pycryptobot options ####
As of version 6.3.0, the option to use custom strategies has been added as well as using the pandas-ta library from Kevin Johnson (twopirllc).  https://github.com/twopirllc/pandas-ta
TA-Lib from John Benediktsson (mrjbq7) https://github.com/mrjbq7/ta-lib is also an option to be used in conjunction with pandas-ta.

This is an separate, advanced section of this file because any editting requires SOME basic Python knowledge to make edits and more Python and pandas dataframe knowledge to make more complicated edits.

New files:
* models/Trading_Pta.py is a new version of the original Trading.py file that has been editted to use the pandas-ta library, if pandas-ta is installed and enabled in the config.json file.
* models/Strategy_CS.py is an addition to the original Strategy.py file and is used specifically for new indicators added in Trading_Pta.py and has a new, weighted buy/sell signal system.
* requirement-advanced.txt is an additiona requirements text file that is used to install the pandas-ta library.  It works just like the original requirements.txt file for other Python modules, but is separated for those who do not want to use pandas-ta and the custom strategy files.  This file can be used in the future for optional modules for advanced features as well.
* pandas_ta_help.py is a separate Python script for getting help with pandas-ta features and functions.  Rather than explaining how to use the pandas-ta help here, please refer to:  https://github.com/twopirllc/pandas-ta#help
* config.json.advance.sample is a sample config with the required settings to use custom strategies as well as some of the other recent features of pycryptobot.

Optional files:
* models/Trading_myPta.py - to customize any of the indicators in Trading_Pta.py or add new ones, make a copy of Trading_Pta.py and rename it to Trading_myPta.py.
* models/Strategy_myCS.py - to change weighted points settings, customize signal requirements or add new one, make a copy of Strategy_CS.py and rename it to Strategy_myCS.py.
    These files are both detected automatically, if they exist, and will prevent any customization from being overwritten by future git updates.  Neither is a requirement and making a copy of one by itself will work fine.  Both the original and the new custom "my" versions can exist together.  If a version exists with "my" in the filename, that will be loaded first.  If the "my" version does not exist, the original will be used instead.  If both versions exist and you choose to use the original/default, either move or rename the "my" version to prevent it from being loaded.
Note:  For the above custom files, please note the addition of "my" to the files names.

Optional TA-Lib installation.  Per the pandas-ta documentation, if TA-Lib is installed, the formulas from TA-Lib will be used in place of the pandas-ta formulas.  Pycryptobot has been programmed to do the same.  After reading the pandas-ta documentation, if you would like to use TA-Lib, just install the library.  Pycryptobot will check if it's installed and if it is, enable it automatically.  If you would like to disable it later, use the myPta file and set the use_talib variable to False.


To use pandas-ta and custom strategies, you will need 2 options added to your config.json file:

* "enable_pandas_ta": 1     will enable pandas-ta and Trading_Pta.py.  This can be used without custom strategies and will use the original, default trading signal settings as described above in this file.
* "enable_custom_strategies": 1     will enable custom strategies with Strategy_CS.py.  The default Strategy_CS.py requires pandas-ta to be enabled as many of the additional indicators and signals are not in the original Trading.py file.


Initial setup:  (It is assumed that you have already gotten the basic installation and configuration completed as described above.)

* Install pandas-ta library with:  python3 -m pip install -r requirements-advanced.txt
* Optionally install TA-Lib per the documentation for the library found on github.
* Add above settings to config.json file per preference.
* Launch pycryptobot.py as you would for the standard configuration.

To make edits to anything in the new trading or strategy files, make copies and name them as described above.

Weighted point system found near the top of Strategy_CS.py in the tradeSignals function:

    Custom strategies use a weight points system to trigger buys and sells.  Each indicator is set to add 1 or 2 points based on standard or strong signal strength.  When the total points matches the settings listed, the respective trade will be signaled and then trailingbuy or trailingsell will kick in as on any other trade.

    The below are the defaults as currently set in Strategy_CS.py

        # max possible points - this is used if sell_trigger_override setting is True, this value is used (see optional settings below)
        self.max_pts = 11
        # total points required to buy
        self.pts_to_buy = 8 # more points requires more signals to activate, less risk
        # total points to trigger immediate buy if trailingbuyimmediatepcnt is configured, else ignored
        self.immed_buy_pts = 10
        # use adjusted buy pts? Subtract any sell_pts from buy_pts before signaling a buy
        # Set to True or False, default is false if not added
        self.use_adjusted_buy_pts = True

        # total points required to sell
        self.pts_to_sell = 3 # requiring fewer pts results in quicker sell signal
        # total points to trigger immediate sell if trailingsellimmediatepcnt is configured, else ignored
        self.immed_sell_pts = 6

        # Required signals.
        # Specify how many have to be triggered
        # Buys - currently 2 of ADX, OBV or MACDLeader - add self.pts_sig_required_buy += 1 to section for each signal
        self.sig_required_buy = 2
        # Sells - currently 2 of OBV, MACDLeader or EMA/WMA - add self.pts_sig_required_sell += 1 to section for each signal
        self.sig_required_sell = 2 # set to 0 for default

    Each indicator has this line for buy pts:
        self.buy_pts += 1
    and for strong (if it has a strong value):
        self.buy_pts += 2

    And for selling, sell pts:
        self.sell_pts += 1
    strong sell (if exists):
        self.sell_pts += 2

    If wanting to disable a particular indicator, you can either comment out the points lines for that indicator or change the value to 0.  If you don't want a strong level for an indicator, do the same for the += 2 line.

Most of the points system should be self explanatory based on the descriptions above.  Required signals is an additional option over and above just the standard points.
If you want to make sure a specific signal or multiple signals are definitely active for either the buy or sell, add the required line as listed above to that signal.  As you can see, the default added required pts for both buy and sell to 3 indicators, but only requires 2 for each one.  The defaults are a result of much testing, but you may have different results and choose different settings for everything.
The idea is that you can customize almost anything you want, based on your own trading strategies.

Optional config settings:

* "selltriggeroverride": 1      if enabled AND all buys signals are active AND all buy signals are STRONG, any of the built in immediate sell triggers (preventloss, trailing stoploss, etc.) will be bypassed temporarily.  See max possible pts above.  As soon as total points are below the max setting, sell triggers will be active again.  This is designed to prevent selling on a small dip in self.price, which is somewhat normal when the self.price is still climbing and all indicators are active.

**Please note:  the trading indicators being used in Strategy_CS.py are NOT using all the traditional methods of generating buy and sell signals.  The idea of custom strategies is to allow users to ability to customize trade indciators in many ways and use some different views of looking at indicators.  After comparing with many charts (mostly on TradingView) some additional patterns were frequent and implemented to hopefully help prevent buying too early or selling too late.  Not every person using this software will agree with the settings being used which is why all of it is 100% customizable.  Strategy files can now be shared with other users as well.  If you don't have the technical ability to customize the code in these files, it doesn't take much reading to get a basic idea of what is needed for minor revisions.  Please put in some effort to understand the market charts and how the various indicators are designed to work before making comments or asking someone else to make customizations for you.  The pycryptobot community is filled with helpful people that are more than will to discuss trading ideas and help others use this trading bot. Please feel free to start a new discussion in our Telegram channels.
