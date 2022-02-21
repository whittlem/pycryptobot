import os
import sys
import unittest
# pylint: disable=import-error
from models.telegram import (
    TelegramActions,
    TelegramControl,
    TelegramHandler,
    TelegramHelper,
    Wrapper,
)

sys.path.append(".")

# helper = TelegramHelper("config.json")
# helper.datafolder = os.path.join(os.curdir, "tests", "unit_tests", "data")
# actions = TelegramActions(helper)
# control = TelegramControl(helper)
# handler = TelegramHandler(helper.config["telegram"]["user_id"], helper)

wrapper = Wrapper("config.json")
wrapper.helper.datafolder = os.path.join(os.curdir, "tests", "unit_tests", "data")
actions = TelegramActions(wrapper.helper)
control = TelegramControl(wrapper.helper)
handler = TelegramHandler(wrapper.helper.config["telegram"]["user_id"], wrapper.helper)

# helper.datafolder = os.path.join(os.curdir, "tests", "unit_tests", "data")
MARKET = "TESTUSDT"

def test_helper_isnot_null():  # pylint: disable=missing-function-docstring
    assert wrapper.helper is not None

def test_margins():  # pylint: disable=missing-function-docstring
    assert wrapper.helper.read_data(MARKET)
    assert actions._get_margin_text(MARKET)

def test_get_active_bot_list():  # pylint: disable=missing-function-docstring
    result = wrapper.helper.get_active_bot_list("active")
    assert len(result) > 0

def test_is_bot_running():  # pylint: disable=missing-function-docstring
    assert wrapper.helper.is_bot_running(MARKET)

def test_update_bot_control():  # pylint: disable=missing-function-docstring
    wrapper.helper.update_bot_control(MARKET, "stop")
    wrapper.helper.read_data(MARKET)
    assert wrapper.helper.data["botcontrol"]["status"] == "stop"
    wrapper.helper.update_bot_control(MARKET, "active")
    wrapper.helper.read_data(MARKET)
    assert wrapper.helper.data["botcontrol"]["status"] == "active"

def test_actions_isnot_null():  # pylint: disable=missing-function-docstring
    assert actions is not None

def test_control_isnot_null():  # pylint: disable=missing-function-docstring
    assert control is not None

def test_handler_isnot_null():  # pylint: disable=missing-function-docstring
    assert handler is not None

def test_authorised_check():  # pylint: disable=missing-function-docstring
    assert not handler._check_if_allowed("0000000000", None)

def test_get_closed_trades():  # pylint: disable=missing-function-docstring
    assert wrapper.closed_trades() != ""
    
@unittest.skip
def test_get_running_bot_info():  # pylint: disable=missing-function-docstring
    # helper.datafolder = os.path.join(os.curdir, "tests", "unit_tests", "data")
    assert wrapper.running_bot_info() != ""

@unittest.skip
def test_start_market_scanner():  # pylint: disable=missing-function-docstring
    assert wrapper.start_market_scanning(None, None, True, False) != ""
