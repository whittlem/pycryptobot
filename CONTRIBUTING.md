# Contributing Guidelines

The PyCryptoBot project accepts contributions via GitHub pull requests. This document outlines the process to help get your contribution accepted.

## Exchanges

Currently Binance and Coinbase Pro are supported. Please read below for guidelines how to set up your development environment.

### Common

You will need to create a config.json file to use for tests. For example:

```json
{
    "coinbasepro": {
        "api_url": "https://api-public.sandbox.pro.coinbase.com",
        "config": {
            "base_currency": "ADA",
            "quote_currency": "EUR",
            "live": 0
        },
        "api_key_file": "coinbasepro.key"
    },
    "binance": {
        "api_url": "https://testnet.binancefuture.com",
        "config": {
            "base_currency": "ADA",
            "quote_currency": "EUR",
            "live": 0
        },
        "api_key_file": "binance.key"
    }
}
```

### API Keys

#### Binance

In order to create an API key with the Binance Test Network, follow [these guidelines](https://algotrading101.com/learn/binance-python-api-guide/#does-binance-offer-a-demo-account). Name your key `binance.key` and place it in the root of the project next to your `config.json`.

#### Coinbase Pro

Similar to binance, in order to create a key for the Coinbase Pro Test Network, follow [these guidelines](https://docs.pro.coinbase.com/#sandbox). Name your key `coinbasepro.key` and place it in the root of the project next to your `config.json`.
