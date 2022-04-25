"""Wrapper for telegram functions"""
from models.telegram import callbacktags
from models.telegram import TelegramHelper, TelegramActions, TelegramHandler, TelegramControl

class Wrapper:
    """Wrapper for Telegram Functions"""

    def __init__(self, config_file='config.json', log_file_prefix = 'telegram') -> None:
        """Initiate wrapper class"""
        self.helper = TelegramHelper(config_file, log_file_prefix)
        self._actions = TelegramActions(self.helper)
        self._handler = TelegramHandler(
            self.helper.config["telegram"]["user_id"], self.helper
        )
        self._controls = TelegramControl(self.helper)

    def start_market_scanning(
        self,
        scanmarkets: bool = True,
        startbots: bool = True,
        update=None,
        context=None,
    ) -> str:
        """Start market scanning/screening\n
        Add schedule if not already running\v
        Can pass nothing to the function it will use defaults from config"""
        self._handler._check_scheduled_job()
        return self._actions.start_market_scan(
            update, context, self.helper.use_default_scanner, scanmarkets, startbots
        )

    def restart_open_order_pairs(self):
        """Restart any bots that are not running and have open orders"""
        return self._actions.start_open_orders(None, None)

    def running_bot_info(self) -> str:
        """Get running bot information\n
        Telegram notifications will still be sent"""
        return self._actions.get_bot_info()

    def closed_trades(self, days=callbacktags.TRADES24H) -> str:
        """Get closed trades\n
        update can be None\n
        Telegram notifications will still be sent"""
        return self._actions.get_closed_trades(None, days)

    def place_market_buy_order(self, market):
        """Place a market buy order"""
        return self._actions.buy_response(None, None, market)

    def place_market_sell_order(self, market):
        """place a market sell order"""
        return self._actions.sell_response(None, None, market)

    def pause_bot(self, market):
        """place a market sell order"""
        return self._controls.pause_bot_response(None, None, market)

    def resume_bot(self, market):
        """place a market sell order"""
        return self._controls.resume_bot_response(None, None, market)

    def stop_bot(self, market):
        """place a market sell order"""
        return self._controls.stop_bot_response(None, None, market)

    def start_bot(self, market):
        """place a market sell order"""
        return self._controls.start_bot_response(None, None, market)

    def check_schedule_running(self) -> bool:
        """ Check schedule """
        return len(self._handler.scannerSchedule.get_jobs()) > 0
