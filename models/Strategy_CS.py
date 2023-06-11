from datetime import date, datetime, timedelta
from models.AppState import AppState
from utils.PyCryptoBot import truncate as _truncate
from views.PyCryptoBot import RichText
from models.TradingAccount import TradingAccount
from models.exchange.Granularity import Granularity


class Strategy_CS:
    def __init__(self, app, state: AppState) -> None:
        self.app = app
        self.state = state
        self.use_adjusted_buy_pts = False  # default, leave this here and change below
        self.use_adjusted_sell_pts = False  # default, leave this here and change below
        self.myCS = True

        if self.state.pandas_ta_enabled is False:
            raise ImportError(
                "This Custom Strategy requires pandas_ta, but pandas_ta module is not loaded. Are requirements-advanced.txt modules installed?"
            )

        if self.state.trading_myPta is True:
            from models.Trading_myPta import TechnicalAnalysis  # pyright: ignore[reportMissingImports]
        else:
            from models.Trading import TechnicalAnalysis
        self.TA = TechnicalAnalysis

    def tradeSignals(self, data, df, current_sim_date, websocket):

        """
        #############################################################################################
        If customizing this file it is recommended to make a copy and name it Strategy_myCS.py
        It will be loaded automatically if pandas-ta is enabled in configuration and it will not
        be overwritten by future updates.
        #############################################################################################
        """

        # buy indicators - using non-traditional settings
        # *** currently requires pandas-ta module and optional talib

        # create additional DataFrames to analyze for indicators
        # first option is the short_granularity (5m, 15min, 1h, 6h, 1d, etc.)
        # granularity abbreviations can be found in ./models/exchange/Granularity.py
        # next option is websocket if being used, if omitting and enabled websockets later, error will occur
        # self.df_1d = self.addDataFrame("1d", websocket).copy()

        # if only wanting to know EMAbull like smartswitch checks fore, there are already built in
        # functions that will add the required dataframes and return results.  Just use:
        # EMA1hBull = self.app.is1hEMA1226Bull(current_sim_date, websocket)
        # EMA6hBull = self.app.is6hEMA1226Bull(current_sim_date, websocket)

        # name and add the dataframe
        df_1h = self.app.getAdditionalDf("1h", websocket).copy()
        # set variable to call technical analysis in Trading_Pta (or myPta)
        ta_1h = self.TA(df_1h)
        # add any individual signals/inicators or add_all()
        ta_1h.add_ema(5, True)
        ta_1h.add_ema(10, True)
        # retrieve the ta results
        df_1h = ta_1h.get_df()
        # name and create last row reference like main dataframe
        data_1h = self.app.get_interval(df_1h)

        # repeat for any additional, don't recommend more than 1 or 2 additional, adds overhead and API calls
        df_6h = self.app.getAdditionalDf("6h", websocket).copy()
        ta_6h = self.TA(df_6h, self.app.adjusttotalperiods)
        ta_6h.add_ema(5, True)
        ta_6h.add_ema(10, True)
        df_6h = ta_6h.get_df()
        data_6h = self.app.get_interval(df_6h)

        # check ema crossovers (these are not standard period lengths, see comments above)
        EMA1hBull = bool(data_1h["ema5"][0] > data_1h["ema10"][0])
        EMA6hBull = bool(data_6h["ema5"][0] > data_6h["ema10"][0])

        # create some variables to calculate difference between 2 signals
        # these can be used in evaluations below and are not in the dataframe to help keep it cleaner, make
        # changing/adding easier and we only need diff for last row anyway
        # Usage:  self.calcDiff(firstSignal, secondSignal)
        # a negative value means the first signal is below the second signal
        rsi_ma_diff = self.calcDiff(data["rsi14"][0], data["rsima14"][0])  # RSI and MA
        di_diff = self.calcDiff(data["+di14"][0], data["-di14"][0])  # ADX di+ and di-
        macd_sg_diff = self.calcDiff(
            data["macd"][0], data["signal"][0]
        )  # Macd and Signal
        obv_sm_diff = self.calcDiff(data["obv"][0], data["obvsm"][0])  # OBV and SM
        macdl_sg_diff = self.calcDiff(
            data["macdlead"][0], data["macdl_sig"][0]
        )  # MacdLeader and Signal
        sma5_10_diff = self.calcDiff(data["sma5"][0], data["sma10"][0])
        sma10_50_diff = self.calcDiff(data["sma10"][0], data["sma50"][0])
        sma50_100_diff = self.calcDiff(data["sma50"][0], data["sma100"][0])

        # to disable any indicator used in this file, set the buy and sell pts to 0 or comment out
        # the lines for buy and sell pts.
        # ** Be sure to adjust total counts below.

        # max possible points - this is used if selltriggeroverride setting is True, this value is used
        # if using smartswitch granularity, recommend lowering each pt total by 1 pt due to the EMA Bull being disabled
        self.max_pts = 12
        self.sell_override_pts = 10
        # total points required to buy
        self.pts_to_buy = 9  # more points requires more signals to activate, less risk
        # total points to trigger immediate buy if trailingbuyimmediatepcnt is configured, else ignored
        self.immed_buy_pts = 11
        # use adjusted buy or sell pts? Set to True or False, default is false if not added
        # adjusting buy, will subtract sell_pts from total buy_pts before signaling a buy
        self.use_adjusted_buy_pts = True
        # adjusting sell, will subtract buy_pts from total sell_pts before signaling a sell
        self.use_adjusted_sell_pts = False

        # total points required to sell
        self.pts_to_sell = 3  # requiring fewer pts results in quicker sell signal
        # total points to trigger immediate sell if trailingsellimmediatepcnt is configured, else ignored
        self.immed_sell_pts = 6

        # Required signals.
        # Specify how many have to be triggered
        # Buys - currently requires Macd, RSI, OBV - add self.pts_sig_required_buy += 1 to section for each signal
        self.sig_required_buy = 3
        # Sells - currently 0 - add self.pts_sig_required_sell += 1 to section for each signal
        self.sig_required_sell = 0  # set to 0 for default

        # don't edit these, need to start at 0
        self.buy_pts = 0
        self.sell_pts = 0
        self.pts_sig_required_buy = 0
        self.pts_sig_required_sell = 0

        # pts_to_buy and pts_to_sell are adjusted with logic statements below based on market condition
        if (  # if sma5 is below sma10 and both are decreasing, this is badd, sell
            data["sma5"][0] < data["sma10"][0]
            and data["sma5_pc"][0] < 0
            and data["sma10_pc"][0] < 0
        ):
            self.market_trend = "High risk, no buying, Sell NOW!"
            self.pts_to_buy = 100
            self.pts_to_sell = 3
            self.immed_sell_pts = 5
            self.sell_override_pts = 100
        elif (  # if sma5 is above sma 10 and both are increasing, things are getting better see SMA5/SMA10 below for pts
            data["sma5"][0] > data["sma10"][0]
            and data["sma5_pc"][0] > 0.1
            and data["sma10_pc"][0] > 0.1
            and data_1h["ema5_pc"][0] > 0
        ):
            if (  # if sma10 is above sma50 and both or increasing, we are getting even better
                data["sma10"][0] > data["sma50"][0]
                and data["sma50_pc"][0] > 0
                and EMA1hBull is True
                and data_1h["ema5_pc"][0] > 0
                and data_6h["ema5_pc"][0] > 0
            ):  # SMA10/SMA50 points
                self.market_trend = "Less risk, buy medium points"
                self.pts_to_buy = 9
                self.immed_buy_pts = 10
                self.pts_to_sell = 4
                self.immed_sell_pts = 7
                if (  # if sma50 is above sma100 and both increasing, we are much better
                    data["sma50"][0] > data["sma100"][0]
                    and data["sma100_pc"][0] > 0
                    and EMA6hBull is True
                    and data_6h["ema5_pc"][0] > 0
                ):  # SMA50/SMA100 points
                    self.market_trend = "Low risk, buy! buy! buy!"
                    self.pts_to_buy = 8
                    self.immed_buy_pts = 9
                    self.pts_to_sell = 5
                    self.immed_sell_pts = 8
            # SMA5/SMA10 point below
            else:
                self.market_trend = "Risky, don't buy yet"
                self.pts_to_buy = 100
                self.pts_to_sell = 3
                self.immed_sell_pts = 5
                self.sell_override_pts = 100
        # to make this a lower risk config by default, this level is disabled for buying
        #                self.pts_to_buy = 10
        #                self.immed_buy_pts = 11
        else:
            self.market_trend = "Too risky, don't buy yet"
            self.pts_to_buy = 100
            self.pts_to_sell = 3
            self.immed_sell_pts = 5
            self.sell_override_pts = 100
        # to make this a lower risk config by default, this level is disabled for buying
        #            self.pts_to_buy = 10
        #            self.immed_buy_pts = 11

        # RSI with SMMA, percent RSI is above MA for strength
        if (  # Buy when RSI is increasing and above MA by 3%
            rsi_ma_diff >= 3  # 15
            and data["rsima14_pc"][0] > 0
            and data["rsi14_pc"][0] > 0
            # the below two lines are a little close to traditional RSI
            #            and data['rsi14'][0] > 20
            #            and data['rsi14'][0] < 70
        ):
            self.pts_sig_required_buy += 1
            if (
                rsi_ma_diff > 10
                or data["rsi14_pc"][0] >= 3
                # the below two lines are a little close to traditional RSI
                #                and data['rsi14'][0] < 65
                #                and data['rsi14'][0] > 30
            ):
                self.rsi_action = "strongbuy"
                self.buy_pts += 2
            else:
                self.rsi_action = "buy"
                self.buy_pts += 1
        elif data[  # Sell if RSI percent of change is less than 0%  and MA percent of change less than 0 or RSI below MA
            "rsi14_pc"
        ][
            0
        ] < 0 and (
            rsi_ma_diff < 0 or data["rsima14_pc"][0] < 0
        ):
            # self.pts_sig_required_sell += 1
            # Strong when RSI is less than -8% below MA or MA pcnt of change < -3%
            if rsi_ma_diff < -8 or data["rsima14_pc"][0] < -3:
                self.rsi_action = "strongsell"
                self.sell_pts += 2
            else:
                self.rsi_action = "sell"
                self.sell_pts += 1
        else:
            self.rsi_action = "wait"

        # ADX with percentage of difference between DI+ & DI- for strength
        if (  # DI+ above DI- and a difference of 20% and ADX > 20
            data["+di14"][0] > data["-di14"][0]
            and di_diff > 20
            and data["adx14"][0] > 20
        ):
            # self.pts_sig_required_buy += 1
            if (  # Strong if ADX is > 30, DI difference greater than 30%
                data["adx14"][0] > 30 and di_diff > 30
            ):
                self.adx_action = "strongbuy"
                self.buy_pts += 2
            else:
                self.adx_action = "buy"
                self.buy_pts += 1
        elif data["+di14"][0] < data["-di14"][0]:  # Sell if DI+ is below DI-
            # self.pts_sig_required_sell += 1
            if (  # Strong if DI difference is below -10% or DI+ percent of change is less than 0
                di_diff < -10 or data["+di_pc"][0] < 0
            ):
                self.adx_action = "strongsell"
                self.sell_pts += 2
            else:
                self.adx_action = "sell"
                self.sell_pts += 1
        else:
            self.adx_action = "wait"

        # MACD signal variation using EMA Oscillator & SMA Signal
        # in addition to typical > 0 and crossover indicators
        if (  # buy when MACD is climbing and above Signal by 15% or more
            macd_sg_diff > 15
            and data["macd_pc"][0] > 0  # Percent of change > 0 also indicates MACD > 0
        ):
            self.pts_sig_required_buy += 1
            if (  # Strong when difference > 30% or percent of change greater than 8%
                macd_sg_diff > 30 or data["macd_pc"][0] > 8
            ):
                self.macd_action = "strongbuy"
                self.buy_pts += 2
            else:
                self.macd_action = "buy"
                self.buy_pts += 1
        elif data["macd_pc"][0] < 0:  # Sell when macd percent of change is below 0
            # self.pts_sig_required_sell += 1
            if (  # Strong if diff between MACD and SIG is < 0 or macd percent of change less than -8%
                macd_sg_diff < 0 or data["macd_pc"][0] < -8
            ):
                self.macd_action = "strongsell"
                self.sell_pts += 2
            else:
                self.macd_action = "sell"
                self.sell_pts += 1
        else:
            self.macd_action = "wait"

        # OBV and SMA8 - when OBV is above its SMA, buy and sell when below or decreasing
        if (  # Buy when OBV is 0.5% above SMA and SMA change percent >= 0
            obv_sm_diff > 0.5 and data["obvsm_pc"][0] > 0
        ):
            self.pts_sig_required_buy += 1
            self.obv_action = "buy"
            self.buy_pts += 1
        elif (  # Sell when OBV/SMA diff < 0 above SMA percent of change < 0
            obv_sm_diff < 0 or data["obvsm_pc"][0] < 0
        ):
            # self.pts_sig_required_sell += 1
            self.obv_action = "sell"
            self.sell_pts += 1
        else:
            self.obv_action = "wait"

        # MACD Leader signal.....
        # for short trading in pycryptobot, we check that MacdLeader > Macdl_sig and upward trend
        if (  # MACDL above Signal by 1% and MACDL change > 3%
            macdl_sg_diff > 1
            and data["macdlead_pc"][0]
            > 3  # Percent of change > 10 also indicates MACD > 0
        ):
            # self.pts_sig_required_buy += 1
            if (  # Strong when MACDL is above Signal by 30% or macd leader percent of change > 10
                macdl_sg_diff > 30 or data["macdlead_pc"][0] > 10
            ):
                self.macdl_action = "strongbuy"
                self.buy_pts += 2
            else:
                self.macdl_action = "buy"
                self.buy_pts += 1
        elif data["macdlead_pc"][0] < 0:  # Sell when MACDL Starts decreasing
            # self.pts_sig_required_sell += 1
            if (  # Strong when MACDL is < 1% above signal or macd leader percent of change < -5
                macdl_sg_diff < 1 or data["macdlead_pc"][0] < -5
            ):
                self.macdl_action = "strongsell"
                self.sell_pts += 2
            else:
                self.macdl_action = "sell"
                self.sell_pts += 1
        else:
            self.macdl_action = "wait"

        # EMA5/WMA5 crossover signal
        if (  # EMA above WMA and EMA percent of change > 0.1%
            data["ema5"][0] > data["ema5_wma5"][0] and data["ema5_pc"][0] > 0.1
        ):
            # self.pts_sig_required_buy += 1
            if data["ema5_pc"][0] > 5:  # Strong when EMA_pc > 5
                self.emawma_action = "strongbuy"
                self.buy_pts += 2
            else:
                self.emawma_action = "buy"
                self.buy_pts += 1
        elif (  # Sell when EMA starts decreasing (usually is after self.price starting to decrease)
            data["ema5_pc"][0] < 0
        ):
            # self.pts_sig_required_sell += 1
            # strong when ema drops below wma
            if data["ema5"][0] < data["ema5_wma5"][0]:
                self.emawma_action = "strongsell"
                self.sell_pts += 2
            else:
                self.emawma_action = "sell"
                self.sell_pts += 1
        else:
            self.emawma_action = "wait"

        # adjusted buy pts - subtract any sell pts from buy pts
        if self.use_adjusted_buy_pts is True:
            self.buy_pts = self.buy_pts - self.sell_pts

        # adjusted sell pts - subtract any buy pts from sell pts
        if self.use_adjusted_sell_pts is True:
            self.sell_pts = self.sell_pts - self.buy_pts

        if self.app.debug is True:
            indicatorvalues = (
                # Actions
                f"{self.market_trend}\n"
                f"BuyPts: {self.buy_pts} SellPts: {self.sell_pts} Macd Action: {self.macd_action}"
                f" ADX Action: {self.adx_action} RSI Action: {self.rsi_action}"
                "\n"
                f"OBV Action: {self.obv_action} MacdL Action: {self.macdl_action}"
                f" EMAWMA Action: {self.emawma_action} myCS: {self.myCS}"
                "\n"
                # RSI
                f"RSI: {_truncate(data['rsi14'][0], 2)} RSIpc: {data['rsi14_pc'][0]}"
                f"  MA: {_truncate(data['rsima14'][0], 2)} RSIDiff: {rsi_ma_diff}%"
                "\n"
                # OBV
                f"OBV: {_truncate(data['obv'][0], 2)} SM: {_truncate(data['obvsm'][0], 2)}"
                f" Diff: {obv_sm_diff} OBVPC: {data['obv_pc'][0]}"
                "\n"
                # ADX
                f"ADX14: {_truncate(data['adx14'][0], 2)}"
                f" DiDiff: {di_diff} +DIpc: {data['+di_pc'][0]}"
                f" +DI14 {_truncate(data['+di14'][0], 2)} -DI14: {_truncate(data['-di14'][0], 2)}"
                "\n"
                # MACD
                f"Macd: {_truncate(data['macd'][0],6)}"
                f" Sgnl: {_truncate(data['signal'][0],6)} SigDiff: {macd_sg_diff}"
                f" Macdpc: {data['macd_pc'][0]}"
                "\n"
                # MACD_Leader
                f"MacdLead: {_truncate(data['macdlead'][0],6)} MacdL: {_truncate(data['macdl'][0],6)}"
                f" MacdlSig: {_truncate(data['macdl_sig'][0],6)} MacdLeadpc: {data['macdlead_pc'][0]}%"
                f" Diff: {macdl_sg_diff}"
                "\n"
                # EMA 1h and 6h
                f"EMA 1h Bull: {EMA1hBull} EMA5_pc: {data_1h['ema5_pc'][0]} EMA 6h Bull: {EMA6hBull} EMA5_pc: {data_6h['ema5_pc'][0]}"
                "\n"
                # EMA/WMA
                f"EMA5pc: {data['ema5_pc'][0]} EMA5: {_truncate(data['ema5'][0],2)}"
                f" WMA5: {_truncate(data['ema5_wma5'][0],2)}"
                "\n"
                # SMA
                f"SMA5: {_truncate(data['sma5'][0],4)}, {data['sma5_pc'][0]} SMA10: {_truncate(data['sma10'][0],4)}"
                f", {data['sma10_pc'][0]} SMA50: {_truncate(data['sma50'][0],4)}, {data['sma50_pc'][0]}"
                f" SMA100: {_truncate(data['sma100'][0],4)}, {data['sma100_pc'][0]}"
                "\n"
                f"SMA5_10_Diff: {sma5_10_diff} SMA10_50_Diff: {sma10_50_diff} SMA50_100_Diff: {sma50_100_diff}"
                "\n"
                # OHCL
                f"Open: {data['open'][0]} High: {data['high'][0]}"
                f" Close: {data['close'][0]} Low: {data['low'][0]}"
                f" williamsr {_truncate(data['williamsr20'][0],2)}"
            )
            RichText.notify(indicatorvalues, self.app, "info")
        else:
            indicatorvalues = ""

        return indicatorvalues

    def buySignal(self) -> bool:

        # non-Traditional buy signal criteria
        # *** currently requires pandas-ta module and optional talib
        if (
            self.buy_pts >= self.pts_to_buy
            and self.pts_sig_required_buy >= self.sig_required_buy
        ):
            if (
                self.app.trailingbuyimmediatepcnt is not None
                and self.buy_pts >= self.immed_buy_pts
            ):
                self.state.trailing_buy_immediate = True
            else:
                self.state.trailing_buy_immediate = False

            return True
        else:
            return False

    def sellSignal(self) -> bool:

        # non-Traditional sell signal criteria
        # *** currently requires pandas-ta module and optional talib
        if (
            self.sell_pts >= self.pts_to_sell
            and self.pts_sig_required_sell >= self.sig_required_sell
        ):
            if (
                self.app.trailingsellimmediatepcnt is not None
                and self.sell_pts >= self.immed_sell_pts
            ):
                self.state.trailing_sell_immediate = True
            else:
                self.state.trailing_sell_immediate = False

            return True
        else:
            return False

    def calcDiff(self, first, second) -> None:

        # used to calculate the difference between two values as a percentage
        # negative result means first value is below second value
        return round((first - second) / abs(first) * 100, 2)

    def setCoTime(self, first, second, coTime):

        # save the time when a crossover occurs, or if just starting the bot, save current time

        if first > second:
            if coTime is None:
                return datetime.now().time()
            else:
                return coTime
        else:
            return None

    def checkGtTime(self, coTime, length):  # -> bool:

        # used to calculate how long the crossover has been in place
        # currently variables in place for SMA crossovers only
        # self.app.sma5gtsma10time, self.app.sma10gtsma50time, self.app.sma50gtsma100time

        if coTime is not None and (
            (
                datetime.combine(date.min, datetime.now().time())
                - datetime.combine(date.min, coTime)
            )
            > timedelta(minutes=length)
        ):
            return (
                True,
                (
                    datetime.combine(date.min, datetime.now().time())
                    - datetime.combine(date.min, coTime)
                ),
            )
        else:
            return (False, 0)
