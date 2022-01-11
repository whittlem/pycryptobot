import os, json, sys

sys.path.append(".")
# pylint: disable=import-error
from models.telegram.actions import TelegramActions
from models.telegram.control import TelegramControl
from models.telegram.handler import TelegramHandler
from models.telegram.helper import TelegramHelper

with open(os.path.join("config.json.sample"), "r", encoding="utf8") as json_file:
        config = json.load(json_file)

helper = TelegramHelper("./tests/unit_tests/data", config, "config.json")
actions = TelegramActions("./tests/unit_tests/data", helper)
control = TelegramControl("./tests/unit_tests/data", helper)
handler = TelegramHandler("./tests/unit_tests/data", config["telegram"]["user_id"], helper)

market = "TESTUSDT"

def test_helper_isnot_null():
    assert helper is not None

def test_margins():
    assert helper.read_data(market)
    assert actions._get_margin_text(market)

def test_get_active_bot_list():
    result = helper.get_active_bot_list("active")
    assert len(result) > 0

def test_is_bot_running():
    assert helper.is_bot_running(market)

def test_updateBotcontrol():
    helper.update_bot_control(market, "stop")
    helper.read_data(market)
    assert helper.data["botcontrol"]["status"] == "stop"
    helper.update_bot_control(market, "active")
    helper.read_data(market)
    assert helper.data["botcontrol"]["status"] == "active"
    
def test_actions_isnot_null():
    assert actions is not None

def test_control_isnot_null():
    assert control is not None

def test_handler_isnot_null():
    assert handler is not None

def test_authorised_check():
    assert handler._check_if_allowed("0000000000", None)
