from datetime import datetime
from pandas import DataFrame
from models.PyCryptoBot import PyCryptoBot
from models.AppState import AppState
from models.helper.LogHelper import Logger

class Strategy():
    def __init__(self, app: PyCryptoBot=None, state: AppState=AppState, df: DataFrame=DataFrame, iterations: int=0) -> None:
        if not isinstance(df, DataFrame):
            raise TypeError("'df' not a Pandas dataframe")

        if len(df) == 0:
            raise ValueError("'df' is empty")

        self._action = 'WAIT'
        self.app = app
        self.state = state
        self._df = df
        self._df_last = app.getInterval(df, iterations)


    def isBuySignal(self, now: datetime = datetime.today().strftime('%Y-%m-%d %H:%M:%S'), price: float=0.0) -> bool:
        # required technical indicators or candle sticks for buy signal strategy
        required_indicators = [ 'ema12gtema26co', 'macdgtsignal', 'goldencross', 'obv_pc', 'eri_buy' ]

        for indicator in required_indicators:
            if indicator not in self._df_last:
                raise AttributeError(f"'{indicator}' not in Pandas dataframe")

        # buy signal exclusion (if disabled, do not buy within 3% of the dataframe close high)
        if self.state.last_action == 'SELL' and self.app.disableBuyNearHigh() is True and (price > (self._df['close'].max() * 0.97)):
            log_text = str(now) + ' | ' + self.app.getMarket() + ' | ' + self.app.printGranularity() + ' | Ignoring Buy Signal (price ' + str(price) + ' within 3% of high ' + str(self._df['close'].max()) + ')'
            Logger.warning(log_text)

            return False
        
        # if EMA, MACD are disabled, do not buy
        if self.app.disableBuyEMA() and self.app.disableBuyMACD() :
            log_text = str(now) + ' | ' + self.app.getMarket() + ' | ' + self.app.printGranularity() + ' | EMA, MACD indicators are disabled '
            Logger.warning(log_text)
            
            return False

        # criteria for a buy signal 1
        if (bool(self._df_last['ema12gtema26co'].values[0]) is True or self.app.disableBuyEMA())\
                and (bool(self._df_last['macdgtsignal'].values[0]) is True or self.app.disableBuyMACD()) \
                and (bool(self._df_last['goldencross'].values[0]) is True or self.app.disableBullOnly()) \
                and (float(self._df_last['obv_pc'].values[0]) > -5 or self.app.disableBuyOBV()) \
                and (bool(self._df_last['eri_buy'].values[0]) is True or self.app.disableBuyElderRay()) \
                and self.state.last_action != 'BUY': # required for all strategies

            Logger.debug('*** Buy Signal ***')
            for indicator in required_indicators:
                Logger.debug(f'{indicator}: {self._df_last[indicator].values[0]}')
            Logger.debug(f'last_action: {self.state.last_action}')

            return True

        # criteria for buy signal 2 (optionally add additional buy singals)
        elif (bool(self._df_last['ema12gtema26co'].values[0]) is True or self.app.disableBuyEMA())\
                and bool(self._df_last['macdgtsignalco'].values[0]) is True \
                and (bool(self._df_last['goldencross'].values[0]) is True or self.app.disableBullOnly()) \
                and (float(self._df_last['obv_pc'].values[0]) > -5 or self.app.disableBuyOBV()) \
                and (bool(self._df_last['eri_buy'].values[0]) is True or self.app.disableBuyElderRay()) \
                and self.state.last_action != 'BUY': # required for all strategies

            Logger.debug('*** Buy Signal ***')
            for indicator in required_indicators:
                Logger.debug(f'{indicator}: {self._df_last[indicator].values[0]}')
            Logger.debug(f'last_action: {self.state.last_action}')

            return True

        return False


    def isSellSignal(self) -> bool:
        # required technical indicators or candle sticks for buy signal strategy
        required_indicators = [ 'ema12ltema26co', 'macdltsignal' ]

        for indicator in required_indicators:
            if indicator not in self._df_last:
                raise AttributeError(f"'{indicator}' not in Pandas dataframe")


        # criteria for a sell signal 1
        if bool(self._df_last['ema12ltema26co'].values[0]) is True \
            and (bool(self._df_last['macdltsignal'].values[0]) is True or self.app.disableBuyMACD()) \
            and self.state.last_action not in ['', 'SELL']:

            Logger.debug('*** Sell Signal ***')
            for indicator in required_indicators:
                Logger.debug(f'{indicator}: {self._df_last[indicator].values[0]}')
            Logger.debug(f'last_action: {self.state.last_action}')

            return True

        return False


    def isSellTrigger(self, price: float=0.0, price_exit: float=0.0, margin: float=0.0, change_pcnt_high: float=0.0, obv_pc: float=0.0, macdltsignal: bool=False) -> bool:
        # loss failsafe sell at fibonacci band
        if self.app.disableFailsafeFibonacciLow() is False and self.app.allowSellAtLoss() and self.app.sellLowerPcnt() is None and self.state.fib_low > 0 and self.state.fib_low >= float(price):
            log_text = '! Loss Failsafe Triggered (Fibonacci Band: ' + str(self.state.fib_low) + ')'
            Logger.warning(log_text)
            self.app.notifyTelegram(self.app.getMarket() + ' (' + self.app.printGranularity() + ') ' + log_text)
            return True

        # loss failsafe sell at trailing_stop_loss
        if self.app.trailingStopLoss() != None and change_pcnt_high < self.app.trailingStopLoss() and (self.app.allowSellAtLoss() or margin > 0):
            log_text = '! Trailing Stop Loss Triggered (< ' + str(self.app.trailingStopLoss()) + '%)'
            Logger.warning(log_text)
            self.app.notifyTelegram(self.app.getMarket() + ' (' + self.app.printGranularity() + ') ' + log_text)
            return True

        # loss failsafe sell at sell_lower_pcnt
        elif self.app.disableFailsafeLowerPcnt() is False and self.app.allowSellAtLoss() and self.app.sellLowerPcnt() != None and margin < self.app.sellLowerPcnt():
            log_text = '! Loss Failsafe Triggered (< ' + str(self.app.sellLowerPcnt()) + '%)'
            Logger.warning(log_text)
            self.app.notifyTelegram(self.app.getMarket() + ' (' + self.app.printGranularity() + ') ' + log_text)
            return True

        # profit bank at sell_upper_pcnt
        if self.app.disableProfitbankUpperPcnt() is False and self.app.sellUpperPcnt() != None and margin > self.app.sellUpperPcnt():
            log_text = '! Profit Bank Triggered (> ' + str(self.app.sellUpperPcnt()) + '%)'
            Logger.warning(log_text)
            self.app.notifyTelegram(self.app.getMarket() + ' (' + self.app.printGranularity() + ') ' + log_text)
            return True

        # profit bank when strong reversal detected
        if self.app.disableProfitbankReversal() is False and margin > 3 and obv_pc < 0 and macdltsignal is True:
            log_text = '! Profit Bank Triggered (Strong Reversal Detected)'
            Logger.warning(log_text)
            self.app.notifyTelegram(self.app.getMarket() + ' (' + self.app.printGranularity() + ') ' + log_text)
            return True

        # profit bank when strong reversal detected
        if self.app.sellAtResistance() is True and margin >= 2 and price > 0 and price != price_exit:
            log_text = '! Profit Bank Triggered (Selling At Resistance)'
            Logger.warning(log_text)
            if not (not self.app.allowSellAtLoss() and margin <= 0):
                self.app.notifyTelegram(self.app.getMarket() + ' (' + self.app.printGranularity() + ') ' + log_text)
            return True

        return False

    def isWaitTrigger(self, margin: float=0.0):
        # configuration specifies to not sell at a loss
        if self.state.action == 'SELL' and not self.app.allowSellAtLoss() and margin <= 0:
            log_text = '! Ignore Sell Signal (No Sell At Loss)'
            Logger.warning(log_text)
            return True

        return False

    def getAction(self):
        if self.isBuySignal():
            return 'BUY'
        elif self.isSellSignal():
            return 'SELL'
        else:
            return 'WAIT'
