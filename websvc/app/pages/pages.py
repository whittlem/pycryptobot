import re
import sys
import datetime

# sys.path.append(".")
# pylint: disable=import-error
from models.Trading import TechnicalAnalysis
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
        <script type="text/css" src="css/app.css"></script>

        <title>PyCryptoBot Web Portal</title>
    </head>
    <body>
    """


def footer() -> str:
    return """
    </body>
    </html>
    """


def is_binance_market_valid(market: str) -> bool:
    p = re.compile(r"^[A-Z0-9]{5,12}$")
    if p.match(market):
        return True
    return False


def is_coinbase_market_valid(market: str) -> bool:
    p = re.compile(r"^[0-9A-Z]{1,20}\-[1-9A-Z]{2,5}$")
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
                        <a class="text-dark" href="/binance">Binance</a>
                    </td>
                </tr>
                <tr>
                    <th scope="row">2</th>
                    <td style="border-left: 1px solid #000;">
                        <a class="text-dark" href="/coinbasepro">Coinbase Pro</a>
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
            resp = api.get_markets_24hr_stats()
            for market in resp:
                if market["lastPrice"] > market["openPrice"]:
                    html += f"""
                    <tr>
                        <th class="table-success" scope="row"><a class="text-dark" href="/binance/{market['symbol']}">{market['symbol']}</a></th>
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
                        <th class="table-danger" scope="row"><a class="text-dark" href="/binance/{market['symbol']}">{market['symbol']}</a></th>
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
                        <th scope="row"><a class="text-dark" href="/binance/{market['symbol']}">{market['symbol']}</a></th>
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

        <br />
        <div class="d-grid gap-2 d-md-flex justify-content-md-center">
        <a class="text-dark" href='/binance'><button class="btn btn-success me-md-2" type="button">Refresh</button></a>
        <a class="text-dark" href='/'><button class="btn btn-dark me-md-2" type="button">Go Back</button></a>
        </div>

        {footer()}
        """

    @staticmethod
    def coinbasepro_markets() -> str:
        def markets():
            html = ""

            api = CPublicAPI()
            resp = api.get_markets_24hr_stats()
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
                        <th class="table-success" scope="row"><a class="text-dark" href="/coinbasepro/{market}">{market}</a></th>
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
                        <th class="table-danger" scope="row"><a class="text-dark" href="/coinbasepro/{market}">{market}</a></th>
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
                        <th scope="row"><a class="text-dark" href="/coinbasepro/{market}">{market}</a></th>
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

        <br />
        <div class="d-grid gap-2 d-md-flex justify-content-md-center">
        <a class="text-dark" href='/coinbasepro'><button class="btn btn-success me-md-2" type="button">Refresh</button></a>
        <a class="text-dark" href='/'><button class="btn btn-dark me-md-2" type="button">Go Back</button></a>
        </div>

        {footer()}
        """

    @staticmethod
    def technical_analysis(exchange: str, market: str, g1, g2, g3) -> str:
        if exchange == "binance":
            if not is_binance_market_valid(market):
                return f"""
                {header()}
                <h4>Invalid Market!</h4>

                <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                <a class="text-dark" href='/{exchange}'><button class="btn btn-primary me-md-2" type="button">Go Back</button></a>
                </div>
                {footer()}
                """
        elif exchange == "coinbasepro":
            if not is_coinbase_market_valid(market):
                return f"""
                {header()}
                <h4>Invalid Market!</h4>

                <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                <a class="text-dark" href='/{exchange}'><button class="btn btn-primary me-md-2" type="button">Go Back</button></a>
                </div>
                {footer()}
                """
        else:
            return "Invalid Exchange!"

        if exchange == "binance":
            api = BPublicAPI()
        if exchange == "coinbasepro":
            api = CPublicAPI()
        ticker = api.get_ticker(market)

        ta = TechnicalAnalysis(api.get_historical_data(market, g1, None))
        ta.add_all()
        df_15m = ta.get_df()
        df_15m_last = df_15m.tail(1)

        ta = TechnicalAnalysis(api.get_historical_data(market, g2, None))
        ta.add_all()
        df_1h = ta.get_df()
        df_1h_last = df_1h.tail(1)

        ta = TechnicalAnalysis(api.get_historical_data(market, g3, None))
        ta.add_all()
        df_6h = ta.get_df()
        df_6h_last = df_6h.tail(1)

        if exchange == "binance":
            exchange_name = "Binance"
        elif exchange == "coinbasepro":
            exchange_name = "Coinbase Pro"

        rsi14_15m_class = "table-normal"
        rsi14_15m_desc = "Uneventful"
        if df_15m_last["rsi14"].values[0] > 70:
            rsi14_15m_class = "table-danger"
            rsi14_15m_desc = "Overbought (Sell)"
        elif df_15m_last["rsi14"].values[0] < 30:
            rsi14_15m_class = "table-success"
            rsi14_15m_desc = "Oversold (Buy)"

        rsi14_1h_class = "table-normal"
        rsi14_1h_desc = "Uneventful"
        if df_1h_last["rsi14"].values[0] > 70:
            rsi14_1h_class = "table-danger"
            rsi14_1h_desc = "Overbought (Sell)"
        elif df_1h_last["rsi14"].values[0] < 30:
            rsi14_1h_class = "table-success"
            rsi14_1h_desc = "Oversold (Buy)"

        rsi14_6h_class = "table-normal"
        rsi14_6h_desc = "Uneventful"
        if df_6h_last["rsi14"].values[0] > 70:
            rsi14_6h_class = "table-danger"
            rsi14_6h_desc = "Overbought (Sell)"
        elif df_6h_last["rsi14"].values[0] < 30:
            rsi14_6h_class = "table-success"
            rsi14_6h_desc = "Oversold (Buy)"

        williamsr14_15m_class = "table-normal"
        williamsr14_15m_desc = "Uneventful"
        if df_15m_last["williamsr14"].values[0] > -20:
            williamsr14_15m_class = "table-danger"
            williamsr14_15m_desc = "Overbought (Sell)"
        elif df_15m_last["williamsr14"].values[0] < -80:
            williamsr14_15m_class = "table-success"
            williamsr14_15m_desc = "Oversold (Buy)"

        williamsr14_1h_class = "table-normal"
        williamsr14_1h_desc = "Uneventful"
        if df_1h_last["williamsr14"].values[0] > -20:
            williamsr14_1h_class = "table-danger"
            williamsr14_1h_desc = "Overbought (Sell)"
        elif df_1h_last["williamsr14"].values[0] < -80:
            williamsr14_1h_class = "table-success"
            williamsr14_1h_desc = "Oversold (Buy)"

        williamsr14_6h_class = "table-normal"
        williamsr14_6h_desc = "Uneventful"
        if df_6h_last["williamsr14"].values[0] > -20:
            williamsr14_6h_class = "table-danger"
            williamsr14_6h_desc = "Overbought (Sell)"
        elif df_6h_last["williamsr14"].values[0] < -80:
            williamsr14_6h_class = "table-success"
            williamsr14_6h_desc = "Oversold (Buy)"

        adx14_15m_class = "table-normal"
        adx14_15m_desc = "Normal Trend"
        if (
            df_15m_last["adx14"].values[0] > 25
            and df_15m_last["ema12"].values[0] >= df_15m_last["ema26"].values[0]
        ):
            adx14_15m_class = "table-success"
            adx14_15m_desc = "Strong Trend Up"
        elif (
            df_15m_last["adx14"].values[0] > 25
            and df_15m_last["ema12"].values[0] < df_15m_last["ema26"].values[0]
        ):
            adx14_15m_class = "table-danger"
            adx14_15m_desc = "Strong Trend Down"
        elif (
            df_15m_last["adx14"].values[0] < 20
            and df_15m_last["ema12"].values[0] >= df_15m_last["ema26"].values[0]
        ):
            adx14_15m_class = "table-success"
            adx14_15m_desc = "Weak Trend Up"
        elif (
            df_15m_last["adx14"].values[0] < 20
            and df_15m_last["ema12"].values[0] < df_15m_last["ema26"].values[0]
        ):
            adx14_15m_class = "table-danger"
            adx14_15m_desc = "Weak Trend Up"

        adx14_1h_class = "table-normal"
        adx14_1h_desc = "Normal Trend"
        if (
            df_1h_last["adx14"].values[0] > 25
            and df_1h_last["ema12"].values[0] >= df_1h_last["ema26"].values[0]
        ):
            adx14_1h_class = "table-success"
            adx14_1h_desc = "Strong Trend Up"
        elif (
            df_1h_last["adx14"].values[0] > 25
            and df_1h_last["ema12"].values[0] < df_1h_last["ema26"].values[0]
        ):
            adx14_1h_class = "table-danger"
            adx14_1h_desc = "Strong Trend Down"
        elif (
            df_1h_last["adx14"].values[0] < 20
            and df_1h_last["ema12"].values[0] >= df_1h_last["ema26"].values[0]
        ):
            adx14_1h_class = "table-success"
            adx14_1h_desc = "Weak Trend Up"
        elif (
            df_1h_last["adx14"].values[0] < 20
            and df_1h_last["ema12"].values[0] < df_1h_last["ema26"].values[0]
        ):
            adx14_1h_class = "table-danger"
            adx14_1h_desc = "Weak Trend Up"

        adx14_6h_class = "table-normal"
        adx14_6h_desc = "Normal Trend"
        if (
            df_6h_last["adx14"].values[0] > 25
            and df_6h_last["ema12"].values[0] >= df_6h_last["ema26"].values[0]
        ):
            adx14_6h_class = "table-success"
            adx14_6h_desc = "Strong Trend Up"
        elif (
            df_6h_last["adx14"].values[0] > 25
            and df_6h_last["ema12"].values[0] < df_6h_last["ema26"].values[0]
        ):
            adx14_6h_class = "table-danger"
            adx14_6h_desc = "Strong Trend Down"
        elif (
            df_6h_last["adx14"].values[0] < 20
            and df_6h_last["ema12"].values[0] >= df_6h_last["ema26"].values[0]
        ):
            adx14_6h_class = "table-success"
            adx14_6h_desc = "Weak Trend Up"
        elif (
            df_6h_last["adx14"].values[0] < 20
            and df_6h_last["ema12"].values[0] < df_6h_last["ema26"].values[0]
        ):
            adx14_6h_class = "table-danger"
            adx14_6h_desc = "Weak Trend Up"

        return f"""
        {header()}

        <div class="container">
            <h4 class="text-center">{exchange_name} - {market}</h4>

            <h6 class="text-center">Last update: {ticker[0]}</h6>
            <h6 class="text-center">Closing price: {'%.08f' % ticker[1]}</h6>

            <br />
            <h5 class="text-center">Moving Averages</h5>

            <div class="row">
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="3">15 Minutes</th>
                        </thead>
                        <thead>
                            <th scope="col">EMA12</th>
                            <th scope="col">EMA26</th>
                            <th scope="col">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{'table-success' if df_15m_last['ema12'].values[0] > df_15m_last['ema26'].values[0] else 'table-danger'}">
                                <td>{'%.08f' % round(df_15m_last['ema12'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_15m_last['ema26'].values[0], 8)}</td>
                                <td>{'EMA12 > EMA26' if df_15m_last['ema12'].values[0] > df_15m_last['ema26'].values[0] else 'EMA12 <= EMA26'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="3">1 Hour</th>
                        </thead>
                        <thead>
                            <th scope="col">EMA12</th>
                            <th scope="col">EMA26</th>
                            <th scope="col">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{'table-success' if df_1h_last['ema12'].values[0] > df_1h_last['ema26'].values[0] else 'table-danger'}">
                                <td>{'%.08f' % round(df_1h_last['ema12'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_1h_last['ema26'].values[0], 8)}</td>
                                <td>{'EMA12 > EMA26' if df_1h_last['ema12'].values[0] > df_1h_last['ema26'].values[0] else 'EMA12 <= EMA26'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="3">6 Hour</th>
                        </thead>
                        <thead>
                            <th scope="col">EMA12</th>
                            <th scope="col">EMA26</th>
                            <th scope="col">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{'table-success' if df_6h_last['ema12'].values[0] > df_6h_last['ema26'].values[0] else 'table-danger'}">
                                <td>{'%.08f' % round(df_6h_last['ema12'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_6h_last['ema26'].values[0], 8)}</td>
                                <td>{'EMA12 > EMA26' if df_6h_last['ema12'].values[0] > df_6h_last['ema26'].values[0] else 'EMA12 <= EMA26'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="row">
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" style="width: 30%">SMA50</th>
                            <th scope="col" style="width: 30%">SMA200</th>
                            <th scope="col" style="width: 40%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{'table-success' if df_15m_last['sma50'].values[0] > df_15m_last['sma200'].values[0] else 'table-danger'}">
                                <td>{'%.08f' % round(df_15m_last['sma50'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_15m_last['sma200'].values[0], 8)}</td>
                                <td>{'SMA50 > SMA200' if df_15m_last['sma50'].values[0] > df_15m_last['sma200'].values[0] else 'SMA50 <= SMA200'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" style="width: 30%">SMA50</th>
                            <th scope="col" style="width: 30%">SMA200</th>
                            <th scope="col" style="width: 40%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{'table-success' if df_1h_last['sma50'].values[0] > df_1h_last['sma200'].values[0] else 'table-danger'}">
                                <td>{'%.08f' % round(df_1h_last['sma50'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_1h_last['sma200'].values[0], 8)}</td>
                                <td>{'SMA50 > SMA200' if df_1h_last['sma50'].values[0] > df_1h_last['sma200'].values[0] else 'SMA50 <= SMA200'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" style="width: 30%">SMA50</th>
                            <th scope="col" style="width: 30%">SMA200</th>
                            <th scope="col" style="width: 40%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{'table-success' if df_6h_last['sma50'].values[0] > df_6h_last['sma200'].values[0] else 'table-danger'}">
                                <td>{'%.08f' % round(df_6h_last['sma50'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_6h_last['sma200'].values[0], 8)}</td>
                                <td>{'SMA50 > SMA200' if df_6h_last['sma50'].values[0] > df_6h_last['sma200'].values[0] else 'SMA50 <= SMA200'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <br />
            <h5 class="text-center">Momentum Indicators</h5>

            <div class="row">
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="3">15 Minutes</th>
                        </thead>
                        <thead>
                            <th scope="col" style="width: 50%">RSI14</th>
                            <th scope="col" style="width: 50%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{rsi14_15m_class}">
                                <td>{'%.08f' % round(df_15m_last['rsi14'].values[0], 8)}</td>
                                <td>{rsi14_15m_desc}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="3">1 Hour</th>
                        </thead>
                        <thead>
                            <th scope="col" style="width: 50%">RSI14</th>
                            <th scope="col" style="width: 50%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{rsi14_1h_class}">
                                <td>{'%.08f' % round(df_1h_last['rsi14'].values[0], 8)}</td>
                                <td>{rsi14_1h_desc}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="3">6 Hour</th>
                        </thead>
                        <thead>
                            <th scope="col" style="width: 50%">RSI14</th>
                            <th scope="col" style="width: 50%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{rsi14_6h_class}">
                                <td>{'%.08f' % round(df_6h_last['rsi14'].values[0], 8)}</td>
                                <td>{rsi14_6h_desc}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="row">
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" style="width: 50%">Williams %R</th>
                            <th scope="col" style="width: 50%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{williamsr14_15m_class}">
                                <td>{'%.08f' % round(df_15m_last['williamsr14'].values[0], 8)}</td>
                                <td>{williamsr14_15m_desc}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" style="width: 50%">Williams %R</th>
                            <th scope="col" style="width: 50%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{williamsr14_1h_class}">
                                <td>{'%.08f' % round(df_1h_last['williamsr14'].values[0], 8)}</td>
                                <td>{williamsr14_1h_desc}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" style="width: 50%">Williams %R</th>
                            <th scope="col" style="width: 50%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{williamsr14_6h_class}">
                                <td>{'%.08f' % round(df_6h_last['williamsr14'].values[0], 8)}</td>
                                <td>{williamsr14_6h_desc}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <br />
            <h5 class="text-center">Trend Indicators</h5>

            <div class="row">
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="3">15 Minutes</th>
                        </thead>
                        <thead>
                            <th scope="col" style="width: 30%">MACD</th>
                            <th scope="col" style="width: 30%">Signal</th>
                            <th scope="col" style="width: 40%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{'table-success' if df_15m_last['macd'].values[0] > df_15m_last['signal'].values[0] else 'table-danger'}">
                                <td>{'%.08f' % round(df_15m_last['macd'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_15m_last['signal'].values[0], 8)}</td>
                                <td>{'MACD > Signal' if df_15m_last['macd'].values[0] > df_15m_last['signal'].values[0] else 'MACD <= Signal'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="3">1 Hour</th>
                        </thead>
                        <thead>
                            <th scope="col" style="width: 30%">MACD</th>
                            <th scope="col" style="width: 30%">Signal</th>
                            <th scope="col" style="width: 40%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{'table-success' if df_1h_last['macd'].values[0] > df_1h_last['signal'].values[0] else 'table-danger'}">
                                <td>{'%.08f' % round(df_1h_last['macd'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_1h_last['signal'].values[0], 8)}</td>
                                <td>{'MACD > Signal' if df_1h_last['macd'].values[0] > df_1h_last['signal'].values[0] else 'MACD <= Signal'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="3">6 Hour</th>
                        </thead>
                        <thead>
                            <th scope="col" style="width: 30%">MACD</th>
                            <th scope="col" style="width: 30%">Signal</th>
                            <th scope="col" style="width: 40%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{'table-success' if df_6h_last['macd'].values[0] > df_6h_last['signal'].values[0] else 'table-danger'}">
                                <td>{'%.08f' % round(df_6h_last['macd'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_6h_last['signal'].values[0], 8)}</td>
                                <td>{'MACD > Signal' if df_6h_last['macd'].values[0] > df_6h_last['signal'].values[0] else 'MACD <= Signal'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="row">
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="2" style="width: 60%">ADX14</th>
                            <th scope="col" style="width: 40%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{adx14_15m_class}">
                                <td colspan="2">{'%.08f' % round(df_15m_last['adx14'].values[0], 8)}</td>
                                <td>{adx14_15m_desc}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="2" style="width: 60%">ADX14</th>
                            <th scope="col" style="width: 40%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{adx14_1h_class}">
                                <td colspan="2">{'%.08f' % round(df_1h_last['adx14'].values[0], 8)}</td>
                                <td>{adx14_1h_desc}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="2" style="width: 60%">ADX14</th>
                            <th scope="col" style="width: 40%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{adx14_6h_class}">
                                <td colspan="2">{'%.08f' % round(df_6h_last['adx14'].values[0], 8)}</td>
                                <td>{adx14_6h_desc}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <br />
            <h5 class="text-center">Volume Indicators</h5>

            <div class="row">
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="3">15 Minutes</th>
                        </thead>
                        <thead>
                            <th scope="col" style="width: 50%">OBV10</th>
                            <th scope="col" style="width: 50%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{'table-success' if df_15m_last['obv'].values[0] > 0 else 'table-danger'}">
                                <td>{'%.0f' % df_15m_last['obv'].values[0]} ({df_15m_last['obv_pc'].values[0]}%)</td>
                                <td>{'OBV > 0' if df_15m_last['obv'].values[0] > 0 else 'OBV <= 0'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="3">1 Hour</th>
                        </thead>
                        <thead>
                            <th scope="col" style="width: 50%">OBV10</th>
                            <th scope="col" style="width: 50%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{'table-success' if df_1h_last['obv'].values[0] > 0 else 'table-danger'}">
                                <td>{'%.0f' % df_1h_last['obv'].values[0]} ({df_1h_last['obv_pc'].values[0]}%)</td>
                                <td>{'OBV > 0' if df_1h_last['obv'].values[0] > 0 else 'OBV <= 0'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="3">6 Hour</th>
                        </thead>
                        <thead>
                            <th scope="col" style="width: 50%">OBV10</th>
                            <th scope="col" style="width: 50%">Status</th>
                        </thead>
                        <tbody>
                            <tr class="{'table-success' if df_6h_last['obv'].values[0] > 0 else 'table-danger'}">
                                <td>{'%.0f' % df_6h_last['obv'].values[0]} ({df_6h_last['obv_pc'].values[0]}%)</td>
                                <td>{'OBV > 0' if df_6h_last['obv'].values[0] > 0 else 'OBV <= 0'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <br />
            <h5 class="text-center">Fibonacci Retracement Levels</h5>

            <div class="row">
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="5">15 Minutes</th>
                        </thead>
                        <thead>
                            <th scope="col" style="width: 20%">23.6%</th>
                            <th scope="col" style="width: 20%">38.2%</th>
                            <th scope="col" style="width: 20%">50%</th>
                            <th scope="col" style="width: 20%">61.8%</th>
                            <th scope="col" style="width: 20%">78.6%</th>
                        </thead>
                        <tbody>
                            <tr class="{rsi14_15m_class}">
                                <td>{'%.08f' % round(df_15m_last['fbb_lower0_236'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_15m_last['fbb_lower0_382'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_15m_last['fbb_lower0_5'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_15m_last['fbb_lower0_618'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_15m_last['fbb_lower0_786'].values[0], 8)}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="row">
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="5">1 Hour</th>
                        </thead>
                        <thead>
                            <th scope="col" style="width: 20%">23.6%</th>
                            <th scope="col" style="width: 20%">38.2%</th>
                            <th scope="col" style="width: 20%">50%</th>
                            <th scope="col" style="width: 20%">61.8%</th>
                            <th scope="col" style="width: 20%">78.6%</th>
                        </thead>
                        <tbody>
                            <tr class="{rsi14_15m_class}">
                                <td>{'%.08f' % round(df_1h_last['fbb_lower0_236'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_1h_last['fbb_lower0_382'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_1h_last['fbb_lower0_5'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_1h_last['fbb_lower0_618'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_1h_last['fbb_lower0_786'].values[0], 8)}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="row">
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" colspan="5">6 Hours</th>
                        </thead>
                        <thead>
                            <th scope="col" style="width: 20%">23.6%</th>
                            <th scope="col" style="width: 20%">38.2%</th>
                            <th scope="col" style="width: 20%">50%</th>
                            <th scope="col" style="width: 20%">61.8%</th>
                            <th scope="col" style="width: 20%">78.6%</th>
                        </thead>
                        <tbody>
                            <tr class="{rsi14_15m_class}">
                                <td>{'%.08f' % round(df_6h_last['fbb_lower0_236'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_6h_last['fbb_lower0_382'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_6h_last['fbb_lower0_5'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_6h_last['fbb_lower0_618'].values[0], 8)}</td>
                                <td>{'%.08f' % round(df_6h_last['fbb_lower0_786'].values[0], 8)}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <br />
            <h5 class="text-center">Seasonal ARIMA Model Predictions</h5>

            <div class="row">
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" style="width: 50%">Time</th>
                            <th scope="col" style="width: 50%">Prediction</th>
                        </thead>
                    </table>
                </div>
                <div class="col-sm">
                    <table class="table table-sm table-light table-hover table-striped">
                        <thead>
                            <th scope="col" style="width: 50%">Time</th>
                            <th scope="col" style="width: 50%">Prediction</th>
                        </thead>
                    </table>
                </div>
            <div>

        </div>

        <br />
        <div class="d-grid gap-2 d-md-flex justify-content-md-center">
        <a class="text-dark" href='/{exchange}/{market}'><button class="btn btn-success me-md-2" type="button">Refresh</button></a>
        <a class="text-dark" href='/{exchange}'><button class="btn btn-dark me-md-2" type="button">Go Back</button></a>
        </div>

        {footer()}
        """   # noqa: W292
