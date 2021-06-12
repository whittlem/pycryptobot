[![Docker](https://github.com/whittlem/pycryptobot/actions/workflows/container.yml/badge.svg)](https://github.com/whittlem/pycryptobot/actions/workflows/container.yml/badge.svg) [![Tests](https://github.com/whittlem/pycryptobot/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/whittlem/pycryptobot/actions/workflows/unit-tests.yml/badge.svg)

# Python Crypto Bot v2.30.2 (pycryptobot)

## Join our chat on Telegram

https://t.me/joinchat/09hYKfelbRY2MDNk

##  Supporting The Project

I get paid to write on Medium. Readers following me, applauding and commenting on my articles, all helps with my earnings. I provided this bot to all of you for free and actively developing it. One way you can support my efforts is to follow me on Medium and read my articles. The Medium subscription is $5 a month (roughly £3) so basically nothing in terms of the value you are getting from the bot. Your efforts here would be greatly appreciated!

Follow me on Medium for updates!

https://whittle.medium.com

Python Crypto Bot (PyCryptoBot)

https://medium.com/coinmonks/python-crypto-bot-pycryptobot-b54f4b3dbb75

What’s new in PyCryptoBot 2?

https://medium.com/coinmonks/whats-new-in-pycryptobot-2-a4bbb1b0c90e

PyCryptoBot with Telegram

https://medium.com/coinmonks/pycryptobot-with-telegram-83eed5f230c2

PyCryptoBot Results and Config

https://medium.com/coinmonks/pycryptobot-results-and-config-57fb6625a6d9

Coinbase Pro Portfolio Tracker

https://medium.com/coinmonks/coinbase-pro-portfolio-tracker-a6e4a1c6b8f8

TradingView.com Charts ❤

https://levelup.gitconnected.com/tradingview-com-charts-36a49c9f77ea

## Optional Add-on

Coinbase Pro Portfolio Tracker

https://github.com/whittlem/coinbaseprotracker

An all-in-one view of all your Coinbase Pro portfolios. Highly recommended
if running multiple bots and keeping track of their progress.

## Prerequisites

* When running in containers: a working docker/podman installation

* Python 3.9.x installed -- https://installpython3.com  (must be Python 3.9 or greater)

    % python3 --version

    Python 3.9.1

* Python 3 PIP installed -- https://pip.pypa.io/en/stable/installing

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

### Manual:

    % python3 pycryptobot.py <arguments>

### Docker (Option 1):

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

### docker-compose (Option 2):

To run using the config.json in template folder,

    % docker-compose up -d


By default, docker-compose will use the config inside `./market/template`. We provide this as a template for any market config.

For each market you want to trade, create a copy of this folder under market
For example, if you are trading `BTCEUR` and `ETHEUR` your market folder should look like this:
```
├── market
│ ├── BTCEUR
│ │ ├── config.json
│ │ ├── pycryptobot.log
│ │ └── graphs
│ └── ETHEUR
│   ├── config.json
│   ├── pycryptobot.log
│   └── graphs
```

modify docker-compose.yaml

    version: "3.9"

    services:
      btceur:
        build:
          context: .
        container_name: btceur
        volumes:
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

Sell signal:

* EMA12 is currently crossing below the EMA26
* MACD is below the Signal

Special sell cases:

* "buymaxsize" specify a fixed max amount of the quote currency to buy with
* If "sellatloss" is on, bot will sell if price drops below the lower Fibonacci band
* If "sellatloss" is on and "selllowerpcnt" is specified the bot will sell at the specified amount E.g. -2 for -2% margin
* If "sellatloss" is on and "trailingstoploss" is specified the bot will sell at the specified amount below the buy high
* If "sellupperpcnt" is specified the bot will sell at the specified amount E.g. 10 for 10% margin (Depending on the conditions I lock in profit at 3%)
* If the margin exceeds 3% and the price reaches a Fibonacci band it will sell to lock in profit
* If the margin exceeds 3% but a strong reversal is detected with negative OBV and MACD < Signal it will sell
* "sellatloss" set to 0 prevents selling at a loss

## Optional Options

    --autorestart                       Automatically restart the bot on error
    --sellatresistance                  Sells if the price reaches either resistance or Fibonacci band

## Disabling Default Functionality

    --disablebullonly                   Disable only buying in bull market
    --disablebuynearhigh                Disable buying within 3% of the dataframe high
    --disablebuymacd                    Disable macd buy signal
    --disablebuyobv                     Disable obv buy signal
    --disablebuyelderray                Disable elder ray buy signal
    --disablefailsafefibonaccilow       Disable failsafe sell on fibonacci lower band
    --disablefailsafelowerpcnt          Disable failsafe sell on 'selllowerpcnt'
    --disableprofitbankupperpcnt        Disable profit bank on 'sellupperpcnt'
    --disableprofitbankfibonaccihigh    Disable profit bank on fibonacci upper band
    --disableprofitbankreversal         Disable profit bank on strong candlestick reversal
    --disabletelegram                   Disable sending telegram messages
    --disablelog                        Disable writing log entries
    --disabletracker                    Disable saving CSV on buy and sell events

## "Sell At Loss" explained

The "sellatloss" option disabled has it's advantages and disadvantages. It does prevent any losses but also prevents you from exiting a market before a crash or bear market. Sometimes it's better to make an occasional small loss and make it up with several buys than be conservative and potentially lock a trade for weeks if not months. It happened to me while testing this with the last crash (after Elon's tweet!). Three of my bots did not sell while the profit dropped to -10 to -20%. It did bounce back and I made over 3% a trade with any losses but I also lost out of loads of trading opportunities. It's really a matter of preference. Maybe some markets would be more appropriate than others for this.

## Live Trading

In order to trade live you need to authenticate with the Coinbase Pro or Binance APIs. This is all documented in my Medium articles. In summary you will need to include a config.json file in your project root which contains your API keys. If the file does not exist it will only work in test/demo mode.

## Trading Simulation

    --sim ['fast, fast-sample, slow-sample']   Sets simulation mode
    --simstartdate                             Start date for sample simulation e.g '2021-01-15'
    --simenddate                               End date for sample simulation or 'now'

`simstartdate` takes priority over `simenddate` if both are given

## config.json examples

Coinbase Pro basic (using smart switching)

    {
        "api_url" : "https://api.pro.coinbase.com",
        "api_key" : "<removed>",
        "api_secret" : "<removed>",
        "api_pass" : "<removed>",
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
        "api_key" : "<removed>",
        "api_secret" : "<removed>",
        "api_pass" : "<removed>",
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
            "api_key" : "<removed>",
            "api_secret" : "<removed>",
            "api_passphrase" : "<removed>",
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
            "api_key" : "<removed>",
            "api_secret" : "<removed>",
            "config" : {
                "base_currency" : "BTC",
                "quote_currency" : "ZAR",
                "granularity" : "1h",
                "live" : 0,
                "verbose" : 0
            }
        }
    }

Coinbase Pro and Binance (new format)

    {
        "binance" : {
            "api_url" : "https://api.binance.com",
            "api_key" : "<removed>",
            "api_secret" : "<removed>",
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
            "api_key" : "<removed>",
            "api_secret" : "<removed>",
            "api_passphrase" : "<removed>",
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
        "client_id" : "<client id>"
    }

You can use @botfather and @myidbot in telegram to create a bot with token and get a client id.

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

"logfile" is overriden by '--logfile' console argument.
If '--logfile' used when running bot "logfile": "pycryptobot.log" line in config file will be ignored.

"fileloglevel" and "consoleloglevel" can get one of 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'
For further detail in log levels: https://docs.python.org/3/library/logging.html#logging-levels

## Multi-Market Trading

The bot can trade multiple markets at once. This is also documented in my Medium articles. The bot will execute buys using the full "quote currency" balance it has access too and it will sell the full "base currency" balance it has access too. In order to ring-fence your non-bot funds you should create another "Portfolio" in Coinbase Pro and assign API keys to it. That way you limit exposure. You can so something similar with Binance using sub-accounts but I believe you need to be a certain level to do this.

The way you trade multiple markets at once is create multiple Coinbase Pro portfolios for each each bot instance. You will then clone this project for additional bots with the relevant Portfolio keys (config.json).

I have 5 bots running at once for my Portfolios: "Bot - BTC-GBP", "Bot - BCH-GBP", "Bot - ETH-GBP", "Bot - LTC-GBP", and "Bot - XLM-EUR".

Assuming each bot has a config.json that looks similar to this (update the "cryptoMarket" and "fiatMarket" appropriately):

    {
        "api_url" : "https://api.pro.coinbase.com",
        "api_key" : "<removed>",
        "api_secret" : "<removed>",
        "api_pass" : "<removed>",
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

## Upgrading the bots

I push updates regularly and it's best to always be running the latest code. In each bot directory make sure you run this regularly.

    git pull

I've actually included this in the examples in how to start the bot that will do this for you automatically.

## Fun quick non-live demo

    python3 pycryptobot.py --market BTC-GBP --granularity 3600 --sim fast --verbose 0

If you get stuck with anything email me or raise an issue in the repo and I'll help you sort it out. Raising an issue is probably better as the question and response may help others.

Enjoy and happy trading! :)
