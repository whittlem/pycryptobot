# Python Crypto Bot (pycryptobot)

## Introduction

Follow me on Medium for updates!
https://whittle.medium.com

## Prerequisites

* Python 3.x installed -- https://installpython3.com

    % python3 --version
    
    Python 3.9.1
    
* Python 3 PIP installed -- https://pip.pypa.io/en/stable/installing

    % python3 -m pip --version
    
    pip 21.0.1 from /usr/local/lib/python3.9/site-packages/pip (python 3.9)

 * The app should work with Python 3.x, but to avoid issues try run Python 3.8 or higher

## Installation

    git clone https://github.com/whittlem/pycryptobot
    cd pycryptobot
    python3 -m pip install -r requirements.txt

## Additional Information

The "requirements.txt" was created with "python3 -m pip freeze"

## Run it

% python3 pycryptobot.py <arguments>

    * Arguments
    --market <market> (default: BTC-GBP)
        * Coinbase Pro market
    --granularity <granularity> (default: 3600)
        * Supported granularity in seconds
    --live <1 or 0> <default: 0>
        * Is the bot live or in test/demo mode
    --graphs <1 or 0> (default: 0)
        * Save graphs on buy and sell events
    --sim <fast or slow>
        * Run a simulation on last 300 intervals of data
    --verbose <1 or 0> (default: 1)
        * Toggle verbose or minimal output

## Live Trading

In order to trade live you need to authenticate with the Coinbase Pro API. This is all documented in my Medium articles. In summary you will need to include a config.json file in your project root which contains your API keys. If the file does not exist it will only work in test/demo mode.

## Multi-Market Trading

The bot can trade mutiple markets at once. This is also documented in my Medium articles. The bot will execute buys using the full FIAT balance it has access too and it will sell the full crypto balance it has access too. In order to ring-fence your non-bot funds you should create another "Portfolio" in Coinbase Pro and assign API keys to it. That way you limit exposure. 

The way you trade multiple markets at once is create multiple Coinbase Pro portfolios for each each bot instance. You will then clone this project for additional bots with the relevant Portfolio keys (config.json).

I have 4 bots running at once for my Portfolios: "Bot - BTC-GBP", "Bot - BCH-GBP", "Bot - ETH-GBP", and "Bot - ETH-GBP"

The way I run my four bots is as follow:

    BTC-GBP % rm pycryptobot.log; rm orders.csv; git reset --hard; git pull; clear; python3 pycryptobot.py --market BTC-GBP --granularity 3600 --live 1 --verbose 0 --graphs 1

    BCH-GBP % rm pycryptobot.log; rm orders.csv; git reset --hard; git pull; clear; python3 pycryptobot.py --market BCH-GBP --granularity 3600 --live 1 --verbose 0 --graphs 1
    
    ETH-GBP % rm pycryptobot.log; rm orders.csv; git reset --hard; git pull; clear; python3 pycryptobot.py --market ETH-GBP --granularity 3600 --live 1 --verbose 0 --graphs 1
    
    LTC-GBP % rm pycryptobot.log; rm orders.csv; git reset --hard; git pull; clear; python3 pycryptobot.py --market ETH-GBP --granularity 3600 --live 1 --verbose 0 --graphs 1
    
## Fun quick non-live demo

    python3 pycryptobot.py --market BTC-GBP --granularity 3600 --sim fast --verbose 0
    
Enjoy and happy trading! :)
