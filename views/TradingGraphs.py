import sys
sys.path.append('.')
from models.CoinbasePro import CoinbasePro
import matplotlib.pyplot as plt

class TradingGraphs():
    def __init__(self, coinbasepro):
        if not isinstance(coinbasepro, CoinbasePro):
            raise TypeError('Coinbase Pro model required.')

        self.coinbasepro = coinbasepro
        self.df = coinbasepro.getDataFrame()
        self.levels = coinbasepro.getSupportResistanceLevels()

    def renderPriceSupportResistance(self):
        ''' Render Price, Support and Resistance Levels '''

        plt.plot(self.df.close)
        
        plt.ylabel('Price')
        plt.xlabel('Days')

        for level in self.levels:
            plt.hlines(level[1], xmin=level[0], xmax=len(self.df), colors='blue')
        
        # TODO: add dates to X axis

        plt.show()
        