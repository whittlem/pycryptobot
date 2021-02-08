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

% python3 pycryptobot.py

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
