from models.CoinbasePro import CoinbasePro
from views.TradingGraphs import TradingGraphs

coinbasepro = CoinbasePro()
print (coinbasepro.getDataFrame())
coinbasepro.addMovingAverages()
print (coinbasepro.getDataFrame())
coinbasepro.addMomentumIndicators()
print (coinbasepro.getDataFrame())
coinbasepro.calculateOnBalanceVolume()
print (coinbasepro.getDataFrame())
print (coinbasepro.getSupportResistanceLevels())
coinbasepro.saveCSV()

tradinggraphs = TradingGraphs(coinbasepro)
tradinggraphs.renderPriceSupportResistance()