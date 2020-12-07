from models.CoinbasePro import CoinbasePro

coinbasepro = CoinbasePro()
print (coinbasepro.getDataFrame())
coinbasepro.addMovingAverages()
print (coinbasepro.getDataFrame())
coinbasepro.addMomentumIndicators()
print (coinbasepro.getDataFrame())
coinbasepro.saveCSV()