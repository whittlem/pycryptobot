import sys
from flask import Flask, send_from_directory
from models.exchange.Granularity import Granularity
from websvc.app.pages import Pages

app = Flask(__name__, static_url_path="")
pages = Pages()


@app.route("/")
def exchanges():
    return Pages.exchanges()


@app.route("/css/<path:path>")
def send_js(path):
    return send_from_directory("css", path)


@app.route("/js/<path:path>")
def send_css(path):
    return send_from_directory("js", path)


@app.route("/binance")
def binance():
    return Pages.binance_markets()


@app.route("/binance/<market>")
def binance_market(market):
    return Pages.technical_analysis('binance', market, Granularity.FIFTEEN_MINUTES, Granularity.ONE_HOUR, Granularity.SIX_HOURS)


@app.route("/coinbasepro")
def coinbasepro():
    return Pages.coinbasepro_markets()


@app.route("/coinbasepro/<market>")
def coinbasepro_market(market):
    return Pages.technical_analysis('coinbasepro', market, 900, 3600, 21600)
