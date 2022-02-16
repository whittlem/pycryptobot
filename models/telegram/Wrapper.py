"""Wrapper for telegram functions"""
from models.telegram import callbacktags
from models.telegram import TelegramHelper, TelegramActions, TelegramHandler

class Wrapper:
    """Wrapper for Telegram Functions"""

    def __init__(self, helper: TelegramHelper) -> None:
        """Initiate wrapper class"""

        self.helper = helper
        self.actions = TelegramActions(self.helper)
        self.handler = TelegramHandler(
            self.helper.config["telegram"]["user_id"], self.helper
        )

    def start_market_scanning(
        self,
        update=None,
        context=None,
        scanmarkets: bool = True,
        startbots: bool = True,
    ) -> str:
        """Start market scanning/screening"""
        return self.actions.start_market_scan(
            update, context, self.helper.use_default_scanner, scanmarkets, startbots
        )

    def running_bot_info(self, update=None, context=None) -> str:
        """Get running bot infomation"""
        return self.actions.get_bot_info(update, context)

    def closed_trades(self, update=None, days=callbacktags.TRADES24H) -> str:
        """Get closed trades"""
        return self.actions.get_closed_trades(update, days)

    # def
