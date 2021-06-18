import sys
from datetime import datetime, timedelta
from models.PyCryptoBot import PyCryptoBot
from models.TradingAccount import TradingAccount
from models.helper.LogHelper import Logger

class Stats():
    def __init__(self, app: PyCryptoBot=None, account: TradingAccount=None) -> None:
        self.app = app
        self.account = account

    def show(self):
        if self.app.getStats():
            # get completed live orders
            self.app.setLive(1)
            self.orders = self.account.getOrders(self.app.getMarket(), '', 'done')

            # get buy/sell pairs (merge as necessary)
            order_pairs = []
            last_order = None
            # pylint: disable=unused-variable
            for index, row in self.orders.iterrows():
                time = row['created_at'].to_pydatetime()
                if row['action'] == 'buy':
                    if last_order in ['sell', None]:
                        last_order = 'buy'
                        order_pairs.append({'buy': {'time':time, 'size': row['size']}, 'sell': None})
                    else:
                        last_order = 'buy'
                        order_pairs[-1]['buy']['size'] += row['size']
                else:
                    if last_order == None: # first order is a sell (no pair)
                        continue
                    if last_order == 'buy':
                        last_order = 'sell'
                        order_pairs[-1]['sell'] = {'time':time, 'size': row['size']}
                    else:
                        order_pairs[-1]['sell']['size'] += row['size']

            # remove open trade
            if len(order_pairs) > 0:
                if order_pairs[-1]['sell'] == None:
                    order_pairs = order_pairs[:-1]

            # get % gains and delta
            for pair in order_pairs:
                pair['gain'] = ((pair['sell']['size'] - pair['buy']['size']) / pair['buy']['size']) * 100
                pair['delta'] = pair['sell']['size'] - pair['buy']['size']

            # get day/week/month/all time totals
            totals = {'today': [], 'week': [], 'month': [], 'all_time': []}
            today = datetime.today().date()
            lastweek = today - timedelta(days=7)
            lastmonth = today - timedelta(days=30)
            for pair in order_pairs:
                totals['all_time'].append(pair)
                if pair['sell']['time'].date() == today:
                    totals['today'].append(pair)
                if pair['sell']['time'].date() > lastweek:
                    totals['week'].append(pair)
                if pair['sell']['time'].date() > lastmonth:
                    totals['month'].append(pair)

            # prepare data for output
            today_per = [x['gain'] for x in totals['today']]
            week_per = [x['gain'] for x in totals['week']]
            month_per = [x['gain'] for x in totals['month']]
            all_time_per = [x['gain'] for x in totals['all_time']]
            today_gain = [x['delta'] for x in totals['today']]
            week_gain = [x['delta'] for x in totals['week']]
            month_gain = [x['delta'] for x in totals['month']]
            all_time_gain = [x['delta'] for x in totals['all_time']]

            if len(today_per) > 0:
                today_delta = [(x['sell']['time'] - x['buy']['time']).total_seconds() for x in totals['today']]
                today_delta = timedelta(seconds=int(sum(today_delta) / len(today_delta)))
            else: today_delta = '0:0:0'
            if len(week_per) > 0:
                week_delta = [(x['sell']['time'] - x['buy']['time']).total_seconds() for x in totals['week']]
                week_delta = timedelta(seconds=int(sum(week_delta) / len(week_delta)))
            else: week_delta = '0:0:0'
            if len(month_per) > 0:
                month_delta = [(x['sell']['time'] - x['buy']['time']).total_seconds() for x in totals['month']]
                month_delta = timedelta(seconds=int(sum(month_delta) / len(month_delta)))
            else: month_delta = '0:0:0'
            if len(all_time_per) > 0:
                all_time_delta = [(x['sell']['time'] - x['buy']['time']).total_seconds() for x in totals['all_time']]
                all_time_delta = timedelta(seconds=int(sum(all_time_delta) / len(all_time_delta)))
            else: all_time_delta = '0:0:0'

            # popular currencies
            symbol = self.app.getQuoteCurrency()
            if symbol in ['USD', 'AUD', 'CAD', 'SGD', 'NZD']: symbol = '$'
            if symbol == 'EUR': symbol = '€'
            if symbol == 'GBP': symbol = '£'

            today_sum = symbol + ' {:.2f}'.format(round(sum(today_gain), 2)) if len(today_gain) > 0 else symbol + ' 0.00'
            week_sum = symbol + ' {:.2f}'.format(round(sum(week_gain), 2)) if len(week_gain) > 0 else symbol + ' 0.00'
            month_sum= symbol + ' {:.2f}'.format(round(sum(month_gain), 2)) if len(month_gain) > 0 else symbol + ' 0.00'
            all_time_sum = symbol + ' {:.2f}'.format(round(sum(all_time_gain), 2)) if len(all_time_gain) > 0 else symbol + ' 0.00'
            today_percent = str(round(sum(today_per), 4)) + '%' if len(today_per) > 0 else '0.0000%'
            week_percent = str(round(sum(week_per), 4)) + '%' if len(week_per) > 0 else '0.0000%'
            month_percent = str(round(sum(month_per), 4)) + '%' if len(month_per) > 0 else '0.0000%'
            all_time_percent = str(round(sum(all_time_per), 4)) + '%' if len(all_time_per) > 0 else '0.0000%'
            
            trades = 'Number of Completed Trades:'
            gains = 'Percentage Gains:'
            aver = 'Average Time Held (H:M:S):'
            success = 'Total Profit/Loss:'
            width = 30

            Logger.info(f'------------- TODAY : {self.app.getMarket()} --------------')
            Logger.info(trades + ' ' * (width-len(trades)) + str(len(today_per)))
            Logger.info(gains + ' ' * (width-len(gains)) + today_percent)
            Logger.info(aver + ' ' * (width-len(aver)) + str(today_delta))
            Logger.info(success + ' ' * (width-len(success)) + today_sum)
            Logger.info(f'\n-------------- WEEK : {self.app.getMarket()} --------------')
            Logger.info(trades + ' ' * (width-len(trades)) + str(len(week_per)))
            Logger.info(gains + ' ' * (width-len(gains)) + week_percent)
            Logger.info(aver + ' ' * (width-len(aver)) + str(week_delta))
            Logger.info(success + ' ' * (width-len(success)) + week_sum)
            Logger.info(f'\n------------- MONTH : {self.app.getMarket()} --------------')
            Logger.info(trades + ' ' * (width-len(trades)) + str(len(month_per)))
            Logger.info(gains + ' ' * (width-len(gains)) + month_percent)
            Logger.info(aver + ' ' * (width-len(aver)) + str(month_delta))
            Logger.info(success + ' ' * (width-len(success)) + month_sum)
            Logger.info(f'\n------------ ALL TIME : {self.app.getMarket()} ------------')
            Logger.info(trades + ' ' * (width-len(trades)) + str(len(all_time_per)))
            Logger.info(gains + ' ' * (width-len(gains)) + all_time_percent)
            Logger.info(aver + ' ' * (width-len(aver)) + str(all_time_delta))
            Logger.info(success + ' ' * (width-len(success)) + all_time_sum)

            sys.exit()