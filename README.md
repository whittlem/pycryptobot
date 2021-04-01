# Python Crypto Bot v2.0.0 (pycryptobot)

## What's New?

* Bot can now use Binance as well as Coinbase Pro
* Optimised bot mechanics for buy and sell signals
* Added "smart switching" between 15 minute and 1 hour graphs
* Added additional technical indicators and candlesticks
* Improved visual graphs for analysis

## Introduction

Follow me on Medium for updates!
https://whittle.medium.com

## Optional Add-on

Coinbase Pro Portfolio Tracker
https://github.com/whittlem/coinbaseprotracker

An all-in-one view of all your Coinbase Pro portfolios. Highly recommended
if running multiple bots and keeping track of their progress.

## Prerequisites

* Python 3.9.x installed -- https://installpython3.com  (must be Python 3.9 or greater)

    % python3 --version
    
    Python 3.9.1
    
* Python 3 PIP installed -- https://pip.pypa.io/en/stable/installing

    % python3 -m pip --version
    
    pip 21.0.1 from /usr/local/lib/python3.9/site-packages/pip (python 3.9)

## Installation

    git clone https://github.com/whittlem/pycryptobot
    cd pycryptobot
    python3 -m pip install -r requirements.txt

## Additional Information

The "requirements.txt" was created with "python3 -m pip freeze"

## Run it

% python3 pycryptobot.py <arguments>

    * Arguments
    --exchange <exchange> (coinbasepro or binance)
        * Specify the exchange to use, leaving it out defaults to coinbasepro
    --market <market> (coinbase format: BTC-GBP, binance format: BTCGBP)
        * Coinbase Pro market
    --granularity <granularity> (coinbase format: 3600, binance format: 1h)
        * Supported granularity
    --live <1 or 0> (default: 0)
        * Is the bot live or in test/demo mode
    --graphs <1 or 0> (default: 0)
        * Save graphs on buy and sell events
    --sim <fast, fast-sample, slow, slow-sample>
        * Run a simulation on last 300 intervals of data OR on a random 300 intervals (sample)
    --verbose <1 or 0> (default: 1)
        * Toggle verbose or minimal output
    --sellupperpcnt <1-100>
        * (Optional) Force a sell when the margin reaches an upper limit
    --selllowerpcnt <-1-100>
        * (Optional) Force a sell when the margin reaches an lower limit
    --nosellatloss <1 or 0> (default: 0)
        * No not sell at a loss (no small losses but could prevent getting out before a big crash)

Typically I would save all my settings in the config.json but running from the command line I would usually run it like this.

% python3 pycryptobot.py --market BTC-GBP --granularity 3600 --live 1 --verbose 0 --selllowerpcnt -2

## Live Trading

In order to trade live you need to authenticate with the Coinbase Pro or Binance APIs. This is all documented in my Medium articles. In summary you will need to include a config.json file in your project root which contains your API keys. If the file does not exist it will only work in test/demo mode.

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
