"""Plots (and/or saves) the graphical trading data using Matplotlib"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from models.Trading import TechnicalAnalysis
import datetime
import sys
sys.path.append('.')

class TradingGraphs():
    def __init__(self, technicalAnalysis):
        """Trading Graphs object model
    
        Parameters
        ----------
        technicalAnalysis : object
            TechnicalAnalysis object to provide the trading data to visualise
        """

        # validates the technicalAnalysis object
        if not isinstance(technicalAnalysis, TechnicalAnalysis):
            raise TypeError('Coinbase Pro model required.')

        # only one figure can be open at a time, close all open figures
        plt.close('all')

        self.technicalAnalysis = technicalAnalysis

        # stores the pandas dataframe from technicalAnalysis object
        self.df = technicalAnalysis.getDataFrame()

        # stores the support and resistance levels from technicalAnalysis object
        self.levels = technicalAnalysis.supportResistanceLevels()

        # seaborn style plots
        plt.style.use('seaborn')

    def renderBuySellSignalEMA1226(self, saveFile='', saveOnly=False):
        """Render the EMA12 and EMA26 buy and sell signals
        
        Parameters
        ----------
        saveFile : str, optional
            Save the figure
        saveOnly : bool
            Save the figure without displaying it 
        """

        buysignals = self.df[self.df.ema12gtema26co == True]
        sellsignals = self.df[self.df.ema12ltema26co == True]

        plt.subplot(111)
        plt.plot(self.df.close, label="price", color="royalblue")
        plt.plot(self.df.ema12, label="ema12", color="orange")
        plt.plot(self.df.ema26, label="ema26", color="purple")
        plt.ylabel('Price')

        for idx in buysignals.index.tolist():
            plt.axvline(x=idx, color='green')

        for idx in sellsignals.index.tolist():
            plt.axvline(x=idx, color='red')

        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.legend()

        try:
            if saveFile != '':
                plt.savefig(saveFile)
        except OSError:
            raise SystemExit('Unable to save: ', saveFile) 

        if saveOnly == False:
            plt.show()

    def renderBuySellSignalEMA1226MACD(self, saveFile='', saveOnly=False):
        """Render the EMA12, EMA26 and MACD buy and sell signals
        
        Parameters
        ----------
        saveFile : str, optional
            Save the figure
        saveOnly : bool
            Save the figure without displaying it         
        """

        buysignals = ((self.df.ema12gtema26co == True) & (self.df.macdgtsignal == True) & (self.df.obv_pc >= 2)) | ((self.df.ema12gtema26 == True) & (self.df.macdgtsignal == True) & (self.df.obv_pc >= 5)) 
        sellsignals = ((self.df.ema12ltema26co == True) & (self.df.macdltsignal == True)) | ((self.df.ema12gtema26 == True) & (self.df.macdltsignal == True) & (self.df.obv_pc < 0))
        df_signals = self.df[(buysignals) | (sellsignals)]

        ax1 = plt.subplot(211)
        plt.plot(self.df.close, label="price", color="royalblue")
        plt.plot(self.df.ema12, label="ema12", color="orange")
        plt.plot(self.df.ema26, label="ema26", color="purple")
        plt.ylabel('Price')

        action = ''
        last_action = ''
        for idx, row in df_signals.iterrows():
            if row['ema12gtema26co'] == True and row['macdgtsignal'] == True and last_action != 'buy':
                action = 'buy'
                plt.axvline(x=idx, color='green')
            elif row['ema12ltema26'] == True and row['macdltsignal'] == True and action == 'buy':
                action = 'sell'
                plt.axvline(x=idx, color='red')

            last_action = action

        plt.xticks(rotation=90)

        plt.subplot(212, sharex=ax1)
        plt.plot(self.df.macd, label="macd")
        plt.plot(self.df.signal, label="signal")
        plt.legend()
        plt.ylabel('Divergence')
        plt.xticks(rotation=90)

        plt.tight_layout()
        plt.legend()

        try:
            if saveFile != '':
                plt.savefig(saveFile)
        except OSError:
            raise SystemExit('Unable to save: ', saveFile) 

        if saveOnly == False:
            plt.show()

    def renderPriceEMA12EMA26(self, saveFile='', saveOnly=False):
        """Render the price, EMA12 and EMA26
        
        Parameters
        ----------
        saveFile : str, optional
            Save the figure
        saveOnly : bool
            Save the figure without displaying it         
        """

        plt.subplot(111)
        plt.plot(self.df.close, label="price")
        plt.plot(self.df.ema12, label="ema12")
        plt.plot(self.df.ema26, label="ema26")
        plt.legend()
        plt.ylabel('Price')
        plt.xticks(rotation=90)
        plt.tight_layout()

        try:
            if saveFile != '':
                plt.savefig(saveFile)
        except OSError:
            raise SystemExit('Unable to save: ', saveFile) 

        if saveOnly == False:
            plt.show()

    def renderPriceSupportResistance(self, saveFile='', saveOnly=False):
        """Render the price, support and resistance levels
        
        Parameters
        ----------
        saveFile : str, optional
            Save the figure
        saveOnly : bool
            Save the figure without displaying it
        """

        plt.subplot(111)
        plt.plot(self.df.close)
        plt.ylabel('Price')

        for level in self.levels:
            plt.axhline(y=level, color='grey')

        plt.xticks(rotation=90)
        plt.tight_layout()

        try:
            if saveFile != '':
                plt.savefig(saveFile)
        except OSError:
            raise SystemExit('Unable to save: ', saveFile) 

        if saveOnly == False:
            plt.show()

    def renderEMAandMACD(self, saveFile='', saveOnly=False):
        """Render the price, EMA12, EMA26 and MACD
        
        Parameters
        ----------
        saveFile : str, optional
            Save the figure
        saveOnly : bool
            Save the figure without displaying it         
        """

        ax1 = plt.subplot(211)
        plt.plot(self.df.close, label="price")
        plt.plot(self.df.ema12, label="ema12")
        plt.plot(self.df.ema26, label="ema26")
        plt.xticks(self.df.close, rotation='vertical')
        plt.legend()
        plt.ylabel('Price')
        plt.subplot(212, sharex=ax1)
        plt.plot(self.df.macd, label="macd")
        plt.plot(self.df.signal, label="signal")
        plt.legend()
        plt.ylabel('Divergence')
        plt.xticks(rotation=90)
        plt.tight_layout()

        try:
            if saveFile != '':
                plt.savefig(saveFile)
        except OSError:
            raise SystemExit('Unable to save: ', saveFile) 

        if saveOnly == False:
            plt.show()

    def renderSeasonalARIMAModel(self, saveFile='', saveOnly=False):
        """Render the seasonal ARIMA model
        
        Parameters
        ----------
        saveFile : str, optional
            Save the figure
        saveOnly : bool
            Save the figure without displaying it         
        """

        fittedValues = self.technicalAnalysis.seasonalARIMAModelFittedValues()

        plt.plot(self.df['close'], label='original')
        plt.plot(fittedValues, color='red', label='fitted')
        plt.title('RSS: %.4f' % sum((fittedValues-self.df['close'])**2))
        plt.legend()
        plt.ylabel('Price')
        plt.xticks(rotation=90)
        plt.tight_layout()

        try:
            if saveFile != '':
                plt.savefig(saveFile)
        except OSError:
            raise SystemExit('Unable to save: ', saveFile) 

        if saveOnly == False:
            plt.show()

    def renderSeasonalARIMAModelPredictionDays(self, days=30, saveFile='', saveOnly=False):
        """Render the seasonal ARIMA model prediction
        
        Parameters
        ----------
        days     : int
            Number of days to predict
        saveFile : str, optional
            Save the figure
        saveOnly : bool
            Save the figure without displaying it         
        """

        results_ARIMA = self.technicalAnalysis.seasonalARIMAModel()

        df = pd.DataFrame(self.df['close'])
        start_date = df.last_valid_index()
        end_date = start_date + datetime.timedelta(days=days)
        pred = results_ARIMA.predict(start=str(start_date), end=str(end_date), dynamic=True)

        plt.plot(pred, label='prediction')
        plt.ylabel('Price')
        plt.xlabel('Days')
        plt.xticks(rotation=90)
        plt.tight_layout()

        try:
            if saveFile != '':
                plt.savefig(saveFile)
        except OSError:
            raise SystemExit('Unable to save: ', saveFile) 

        if saveOnly == False:
            plt.show()

    def renderSMAandMACD(self, saveFile='', saveOnly=False):
        """Render the price, SMA20, SMA50, and SMA200
        
        Parameters
        ----------
        saveFile : str, optional
            Save the figure
        saveOnly : bool
            Save the figure without displaying it        
        """

        ax1 = plt.subplot(211)
        plt.plot(self.df.close, label="price")
        plt.plot(self.df.sma20, label="sma20")
        plt.plot(self.df.sma50, label="sma50")
        plt.plot(self.df.sma200, label="sma200")
        plt.legend()
        plt.ylabel('Price')
        plt.xticks(rotation=90)
        plt.subplot(212, sharex=ax1)
        plt.plot(self.df.macd, label="macd")
        plt.plot(self.df.signal, label="signal")
        plt.legend()
        plt.ylabel('Price')
        plt.xlabel('Days')
        plt.xticks(rotation=90)
        plt.tight_layout()

        try:
            if saveFile != '':
                plt.savefig(saveFile)
        except OSError:
            raise SystemExit('Unable to save: ', saveFile) 

        if saveOnly == False:
            plt.show()