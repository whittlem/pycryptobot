[![Docker](https://github.com/whittlem/pycryptobot/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/whittlem/pycryptobot/actions/workflows/docker-publish.yml)

# Python Crypto Bot v2.0.0 (pycryptobot)

## What's New?

* The bot can now use both Binance and Coinbase Pro exchanges
* Optimised the bot mechanics for buy and sell signals
* Added "smart switching" between 15 minute and 1 hour graphs
* Added additional technical indicators and candlesticks
* Improved visual graphs for analysis
* The bot is now also packaged in a container image

## Introduction

Follow me on Medium for updates!
https://whittle.medium.com

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

## Additional Information

The "requirements.txt" was created with `python3 -m pip freeze`

## Run it

Manual:

    % python3 pycryptobot.py <arguments>

Container:

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

## Bot mechanics

Smart switching:

* If the EMA12 is greater than the EMA26 on the 1 hour and 6 hour intervals switch to start trading on the 15 minute intervals
* If the EMA12 is lower than the EMA26 on the 1 hour and 6 hour intervals switch back to trade on the 1 hour intervals
* If a "granularity" is specified as an argument or in the config.json then smart switching will be disabled
* Force smart switching between 1 hour and 15 minute intervals with "smartswitch" argument or config option (1 or 0)

Buy signal:

* EMA12 is currently crossing above the EMA26
* MACD is above the Signal
* Golden Cross (SMA50 is above the SMA200) <-- bull market detection
* Elder Ray Buy is True <-- bull market detection

The bot will only trade in a bull market to minimise losses!

Sell signal:

* EMA12 is currently crossing below the EMA26
* MACD is below the Signal

Special sell cases:

* If "sellatloss" is on, bot will sell if price drops below the lower Fibonacci band
* If "sellatloss" is on and "selllowerpcnt" is specified the bot will sell at the specified amount E.g. -2 for -2% margin
* If "sellupperpcnt" is specified the bot will sell at the specified amount E.g. 10 for 10% margin (Depending on the conditions I lock in profit at 3%)
* If the margin exceeds 3% and the price reaches a Fibonacci band it will sell to lock in profit
* If the margin exceeds 3% but a strong reversal is detected with negative OBV and MACD < Signal it will sell
* "sellatloss" set to 0 prevents selling at a loss

## "Sell At Loss" explained

The "sellatloss" option disabled has it's benefits and disadvantages. It does prevent any losses but also prevents you from exiting a market before a crash or bear market. Sometimes it's better to make an occasional small loss and make it up with several buys than be conservative and potentially lock a trade for weeks if not months. It happened to me while testing this with the last crash (after Elon's tweet!). Three of my bots did not sell while the profit dropped to -10 to -20%. It did bounce back and I made over 3% a trade with any losses but I also lost out of loads of trading opportunities. It's really a matter of preference. Maybe some markets would be more appropriate than others for this.

## Live Trading

In order to trade live you need to authenticate with the Coinbase Pro or Binance APIs. This is all documented in my Medium articles. In summary you will need to include a config.json file in your project root which contains your API keys. If the file does not exist it will only work in test/demo mode.

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

## Multi-Market Trading

The bot can trade mutiple markets at once. This is also documented in my Medium articles. The bot will execute buys using the full "quote currency" balance it has access too and it will sell the full "base currency" balance it has access too. In order to ring-fence your non-bot funds you should create another "Portfolio" in Coinbase Pro and assign API keys to it. That way you limit exposure. You can so something similar with Binance using sub-accounts but I believe you need to be a certain level to do this.

The way you trade multiple markets at once is create multiple Coinbase Pro portfolios for each each bot instance. You will then clone this project for additional bots with the relevant Portfolio keys (config.json).

I have 5 bots running at once for my Portfolios: "Bot - BTC-GBP", "Bot - BCH-GBP", "Bot - ETH-GBP", "Bot - ETH-GBP", and "Bot - XLM-EUR".

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
