# Change Log
All notable changes to this project will be documented in this file.

Upgrade version:
- git checkout main
- git pull

Upgrade library dependancies (if required):
- python3 -m pip install -r requirements.txt -U

## [2.47.2] - 2021-07-14

### Changed

-- Fixed missing server time (binance) issue

## [2.47.1] - 2021-07-13

### Changed

-- Fixed simulation date issues

## [2.47.0] - 2021-07-13

### Changed

-- Fixed smartwitch for coinbase historic data limit
-- Fixed smartswitching date sync 

## [2.46.2] - 2021-07-13

### Changed

-- Added --disablebuyema argument

-- Updated README.md

## [2.46.1] - 2021-07-12

### Changed

-- use `granularity` instead of `self.getGranularity`

-- use `granularity` instead of `self.getGranularity()`  in `getHistoricalDateRange()` call

* Update README.md

## [2.46.0] - 2021-07-09

### Changed

-- Increased number of attempts at retrieving previous orders in binance api

## [2.45.2] - 2021-07-08

### Changed

-- Improved ADX technical indicator

### Added

-- Added ATR technical indicator

## [2.45.1] - 2021-07-06

### Changed

-- Fixed ARIMA bug in coinbase pro when frequency not set in dataframe

## [2.45.0] - 2021-07-06

### Added

-- Added ADX technical indicator
-- Added auto migrate API keys to coinbasepro.key and/or binance.key

## [2.44.1] - 2021-07-05

### Changed

-- Updated README.md

## [2.44.0] - 2021-07-05

### Added

-- Added log file rotation

## [2.43.1] - 2021-07-05

### Changed

-- Filter on filled orders only in Binance dataframe


## [2.42.0] - 2021-07-03

### Changed

-- Fixed smartswitch for binance simulation mode and live
-- Fixed smartswitch timings to use sim date instead of just defaulting to current date
-- Update goldencross using the actual sim date in sim mode only
-- Update to check when your last order is buy but your coin balance in 0 switch to buy instead
    - Possible bug if you transfer or convert coins on the exchange instead of selling them
-- Update to use correct market data in sim mode + smartswitching

## [2.41.0] - 2021-07-03

### Added

-- statdetail flag which gives a detailed list of transactions (works with --statstartdate and --statgroup)

## [2.40.0] - 2021-07-03

### Changed

-- Updated validation for Telegram keys

## [2.39.0] - 2021-06-27

### Changed

-- Added "api_key_file" to config to keep credentials out of config files for safety

## [2.38.0] - 2021-06-23

### Changed

-- Added statstartdate flag to ignore trades before a given date in stats function
-- Added statgroup flag to merge stats of multiple currency pairs
-- Fixed stats for coinbase pro

## [2.37.3] - 2021-06-22

### Changed

-- Fixed smart switch back bug

## [2.37.2] - 2021-06-21

### Changed

-- Fixed "simstart" bug

## [2.37.1] - 2021-06-18

### Changed

-- Fixed issue from previous release

## [2.37.0] - 2021-06-18

### Changed

-- Refactored the new stats feature into it's own Stats class
-- Fixed a bug with getOrders() for Coinbase Pro
-- Fixed the rounding issue with precision greater than 4
-- Fixed the dummy account which has been broken with a previous PR
-- Updated unit tests

## [2.31.1] - 2021-06-13
  
### Changed

-- Create default config if missing, avoid creating empty config

## [2.31.0] - 2021-06-13
  
### Changed

-- Separated strategy into Strategy model for custom strategies

## [2.30.2] - 2021-06-12
  
### Changed

-- Minor changes in quote currency extraction (binance.py)

## [2.30.1] - 2021-06-12
  
### Changed

-- Suppressed ARIMA model warning

## [2.30.0] - 2021-06-12
  
### Changed

-- Improved ARIMA model output to console
-- Reduced polling from 2 minutes to 1 minute

## [2.29.0] - 2021-06-11
  
### Added

-- Added the Seasonal ARIMA machine learning model for price predictions

## [2.28.0] - 2021-06-11
  
### Added

-- Added Stochastic RSI and Williams %R technical indicators

## [2.27.0] - 2021-06-08
  
### Changed
  
- Optimised simulations, they run a lot faster now

### Added

-- Added app.getHistoricalDataChained

## [2.26.0] - 2021-06-07
  
### Changed
  
- Updated validation to allow for custom Coinbase Pro passphrases
 
## [2.25.0] - 2021-06-06
  
### Added

- Added CHANGELOG.md
 
### Changed
  
- Removed check for 'fees' on Binance orders which doesn't exist
 
### Fixed
 
- Pandas 'SettingWithCopyWarning' in models/exchange/coinbase_pro/api.py
