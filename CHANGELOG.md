# Change Log
All notable changes to this project will be documented in this file.

Upgrade version:
- git checkout main
- git pull

Upgrade library dependancies (if required):
- python3 -m pip install -r requirements.txt -U

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
