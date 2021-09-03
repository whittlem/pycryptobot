import re
import sys

sys.path.append(".")
# pylint: disable=import-error
from models.exchange.binance import PublicAPI as BPublicAPI
from models.exchange.coinbase_pro import PublicAPI as CPublicAPI


def header() -> str:
    return """
    <!doctype html>
    <html lang="en">
    <head>
        <!-- Required meta tags -->
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <script type="text/javascript" src="https://code.jquery.com/jquery-3.6.0.min.js"></script>

        <script type="text/javascript" src="https://cdn.datatables.net/1.11.0/js/jquery.dataTables.min.js"></script>
        <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.11.0/css/jquery.dataTables.min.css">

        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.0/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-KyZXEAg3QhqLMpG8r+8fhAXLRk2vvoC2f3B09zVXn8CA5QIVfZOJ3BCsw2P0p/We" crossorigin="anonymous">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.0/dist/js/bootstrap.bundle.min.js" integrity="sha384-U1DAWAznBHeqEIlVSCgzq+c9gqGAJn5c/t99JyeKa9xxaYpSvHU5awsuZVVFIhvj" crossorigin="anonymous"></script>

        <script type="text/javascript" src="js/app.js"></script>

        <title>PyCryptoBot Web Portal</title>
    </head>
    <body>
    """


def footer() -> str:
    return """
    </body>
    </html>
    """


def isBinanceMarketValid(market: str) -> bool:
    p = re.compile(r"^[A-Z0-9]{5,12}$")
    if p.match(market):
        return True
    return False


def isCoinbaseMarketValid(market: str) -> bool:
    p = re.compile(r"^[1-9A-Z]{2,5}\-[1-9A-Z]{2,5}$")
    if p.match(market):
        return True
    return False


class Pages:
    def __init__(self) -> None:
        self.mike = 1

    @staticmethod
    def exchanges() -> str:
        return f"""
        {header()}

        <h4>PyCryptoBot Portal</h4>
        <table id="exchanges" class="table table-sm table-light table-hover table-striped">
            <thead>
                <th scope="col">#</th>
                <th style="border-left: 1px solid #000;" scope="col">Exchange</th>
            </thead>
            <tbody>
                <tr>
                    <th scope="row">1</th>
                    <td style="border-left: 1px solid #000;">
                        <a href="/binance">Binance</a>
                    </td>
                </tr>
                <tr>
                    <th scope="row">2</th>
                    <td style="border-left: 1px solid #000;">
                        <a href="/coinbasepro">Coinbase Pro</a>
                    </td>
                </tr>
            </tbody>
        </table>

        {footer()}
        """

    @staticmethod
    def binance_markets() -> str:
        def markets():
            html = ""

            api = BPublicAPI()
            resp = api.getMarkets24HrStats()
            for market in resp:
                if market["lastPrice"] > market["openPrice"]:
                    html += f"""
                    <tr>
                        <th class="table-success" scope="row"><a href="/binance/{market['symbol']}">{market['symbol']}</a></th>
                        <td class="table-success" style="border-left: 1px solid #000;">{market['priceChangePercent']}%</td>
                        <td class="table-success">{market['openPrice']}</td>
                        <td class="table-success">{market['highPrice']}</td>
                        <td class="table-success">{market['lowPrice']}</td>
                        <td class="table-success">{market['lastPrice']}</td>
                        <td class="table-success">{market['quoteVolume']}</td>
                    </tr>
                    """
                elif market["lastPrice"] < market["openPrice"]:
                    html += f"""
                    <tr>
                        <th class="table-danger" scope="row"><a href="/binance/{market['symbol']}">{market['symbol']}</a></th>
                        <td class="table-danger" style="border-left: 1px solid #000;">{market['priceChangePercent']}%</td>
                        <td class="table-danger">{market['openPrice']}</td>
                        <td class="table-danger">{market['highPrice']}</td>
                        <td class="table-danger">{market['lowPrice']}</td>
                        <td class="table-danger">{market['lastPrice']}</td>
                        <td class="table-danger">{market['quoteVolume']}</td>
                    </tr>
                    """
                else:
                    html += f"""
                    <tr>
                        <th scope="row"><a href="/binance/{market['symbol']}">{market['symbol']}</a></th>
                        <td style="border-left: 1px solid #000;">{market['priceChangePercent']}%</td>
                        <td>{market['openPrice']}</td>
                        <td>{market['highPrice']}</td>
                        <td>{market['lowPrice']}</td>
                        <td>{market['lastPrice']}</td>
                        <td>{market['quoteVolume']}</td>
                    </tr>
                    """

            return html

        return f"""
        {header()}

        <h4>Binance</h4>
        <table id="markets" class="table table-sm table-light table-hover">
            <thead>
                <th scope="col">Market</th>
                <th scope="col" style="border-left: 1px solid #000;">Change (24hr)</th>
                <th scope="col">Open (24h)</th>
                <th scope="col">High (24h)</th>
                <th scope="col">Close (24h)</th>
                <th scope="col">Low (24h)</th>
                <th scope="col">Volume (24h)</th>
            </thead>
            <tbody>
                {markets()}
            </tbody>
        </table>

        <div class="d-grid gap-2 d-md-flex justify-content-md-end">
        <a href='/'><button class="btn btn-primary me-md-2" type="button">Go Back</button></a>
        </div>

        {footer()}
        """

    @staticmethod
    def coinbasepro_markets() -> str:
        def markets():
            html = ""

            api = CPublicAPI()
            resp = api.getMarkets24HrStats()
            for market in resp:
                stats_30day_volume = 0
                if "stats_30day" in resp[market]:
                    if "volume" in resp[market]["stats_30day"]:
                        stats_30day_volume = resp[market]["stats_30day"]["volume"]

                stats_24hour_open = 0
                stats_24hour_high = 0
                stats_24hour_close = 0
                stats_24hour_low = 0
                stats_24hour_volume = 0
                if "stats_24hour" in resp[market]:
                    if "open" in resp[market]["stats_24hour"]:
                        stats_24hour_open = resp[market]["stats_24hour"]["open"]
                    if "high" in resp[market]["stats_24hour"]:
                        stats_24hour_high = resp[market]["stats_24hour"]["high"]
                    if "last" in resp[market]["stats_24hour"]:
                        stats_24hour_close = resp[market]["stats_24hour"]["last"]
                    if "low" in resp[market]["stats_24hour"]:
                        stats_24hour_low = resp[market]["stats_24hour"]["low"]
                    if "volume" in resp[market]["stats_24hour"]:
                        stats_24hour_volume = resp[market]["stats_24hour"]["volume"]

                if stats_24hour_close > stats_24hour_open:
                    html += f"""
                    <tr>
                        <th class="table-success" scope="row"><a href="/coinbasepro/{market}">{market}</a></th>
                        <td class="table-success" style="border-left: 1px solid #000;">{stats_30day_volume}</td>
                        <td class="table-success" style="border-left: 1px solid #000;">{stats_24hour_open}</td>
                        <td class="table-success">{stats_24hour_high}</td>
                        <td class="table-success">{stats_24hour_close}</td>
                        <td class="table-success">{stats_24hour_low}</td>
                        <td class="table-success">{stats_24hour_volume}</td>
                    </tr>
                    """
                elif stats_24hour_close < stats_24hour_open:
                    html += f"""
                    <tr>
                        <th class="table-danger" scope="row"><a href="/coinbasepro/{market}">{market}</a></th>
                        <td class="table-danger" style="border-left: 1px solid #000;">{stats_30day_volume}</td>
                        <td class="table-danger" style="border-left: 1px solid #000;">{stats_24hour_open}</td>
                        <td class="table-danger">{stats_24hour_high}</td>
                        <td class="table-danger">{stats_24hour_close}</td>
                        <td class="table-danger">{stats_24hour_low}</td>
                        <td class="table-danger">{stats_24hour_volume}</td>
                    </tr>
                    """
                else:
                    html += f"""
                    <tr>
                        <th scope="row"><a href="/coinbasepro/{market}">{market}</a></th>
                        <td style="border-left: 1px solid #000;">{stats_30day_volume}</td>
                        <td style="border-left: 1px solid #000;">{stats_24hour_open}</td>
                        <td>{stats_24hour_high}</td>
                        <td>{stats_24hour_close}</td>
                        <td>{stats_24hour_low}</td>
                        <td>{stats_24hour_volume}</td>
                    </tr>
                    """

            return html

        return f"""
        {header()}

        <h4>Coinbase Pro</h4>
        <table id="markets" class="table table-sm table-light table-hover">
            <thead>
                <th scope="col">Market</th>
                <th scope="col" style="border-left: 1px solid #000;">Volume (30d)</th>
                <th scope="col" style="border-left: 1px solid #000;">Open (24h)</th>
                <th scope="col">High (24h)</th>
                <th scope="col">Close (24h)</th>
                <th scope="col">Low (24h)</th>
                <th scope="col">Volume (24h)</th>
            </thead>
            <tbody>
                {markets()}
            </tbody>
        </table>

        <div class="d-grid gap-2 d-md-flex justify-content-md-end">
        <a href='/'><button class="btn btn-primary me-md-2" type="button">Go Back</button></a>
        </div>

        {footer()}
        """

    @staticmethod
    def binance_market(market) -> str:
        if not isBinanceMarketValid(market):
            return f"""
            {header()}
            <h4>Invalid Market!</h4>

            <div class="d-grid gap-2 d-md-flex justify-content-md-end">
            <a href='/binance'><button class="btn btn-primary me-md-2" type="button">Go Back</button></a>
            </div>
            {footer()}
            """

        return f"""
        {header()}

        <h4>Binance - {market}</h4>

        <div class="d-grid gap-2 d-md-flex justify-content-md-end">
        <a href='/binance'><button class="btn btn-primary me-md-2" type="button">Go Back</button></a>
        </div>

        {footer()}
        """

    @staticmethod
    def coinbasepro_market(market) -> str:
        if not isCoinbaseMarketValid(market):
            return f"""
            {header()}
            <h4>Invalid Market!</h4>

            <div class="d-grid gap-2 d-md-flex justify-content-md-end">
            <a href='/coinbasepro'><button class="btn btn-primary me-md-2" type="button">Go Back</button></a>
            </div>
            {footer()}
            """

        return f"""
        {header()}

        <h4>Coinbase Pro - {market}</h4>

        <div class="d-grid gap-2 d-md-flex justify-content-md-end">
        <a href='/coinbasepro'><button class="btn btn-primary me-md-2" type="button">Go Back</button></a>
        </div>

        {footer()}
        """
