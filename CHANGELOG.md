# Change Log
All notable changes to this project will be documented in this file.

Upgrade version:
- git checkout main
- git pull

Upgrade library dependancies (if required):
- python3 -m pip install -r requirements.txt -U

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
