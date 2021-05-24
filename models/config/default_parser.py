import re
import sys

def merge_config_and_args(exchange_config, args):
    new_config = {}
    if 'config' in exchange_config and exchange_config['config'] is not None:
        new_config = {**exchange_config['config']}
    for (key, value) in args.items():
        if value is not None and value is not False:
            new_config[key] = value
    return new_config

def isCurrencyValid(currency):
    p = re.compile(r"^[1-9A-Z]{2,5}$")
    return p.match(currency)

def defaultConfigParse(app, config):
    if 'live' in config:
        if isinstance(config['live'], int):
            if config['live'] in [0, 1]:
                app.is_live = config['live']

    if 'verbose' in config:
        if isinstance(config['verbose'], int):
            if config['verbose'] in [0, 1]:
                app.is_verbose = config['verbose']

    if 'graphs' in config:
        if isinstance(config['graphs'], int):
            if config['graphs'] in [0, 1]:
                app.save_graphs = config['graphs']

    if 'sim' in config:
        if isinstance(config['sim'], str):
            if config['sim'] in [ 'slow', 'fast']:
                app.is_live = 0
                app.is_sim = 1
                app.sim_speed = config['sim']

            if config['sim'] in ['slow-sample', 'fast-sample' ]:
                app.is_live = 0
                app.is_sim = 1
                app.sim_speed = config['sim']
                if 'simstartdate' in config:
                    app.simstartdate = config['simstartdate']

    if 'sellupperpcnt' in config:
        if isinstance(config['sellupperpcnt'], (int, str)):
            p = re.compile(r"^[0-9\.]{1,5}$")
            if isinstance(config['sellupperpcnt'], str) and p.match(config['sellupperpcnt']):
                app.sell_upper_pcnt = float(config['sellupperpcnt'])
            elif isinstance(config['sellupperpcnt'], int) and config['sellupperpcnt'] > 0 and config['sellupperpcnt'] <= 100:
                app.sell_upper_pcnt = float(config['sellupperpcnt'])

    if 'selllowerpcnt' in config:
        if isinstance(config['selllowerpcnt'], (int, str)):
            p = re.compile(r"^\-[0-9\.]{1,5}$")
            if isinstance(config['selllowerpcnt'], str) and p.match(config['selllowerpcnt']):
                app.sell_lower_pcnt = float(config['selllowerpcnt'])
            elif isinstance(config['selllowerpcnt'], int) and config['selllowerpcnt'] >= -100 and config['selllowerpcnt'] < 0:
                app.sell_lower_pcnt = float(config['selllowerpcnt'])

    if 'trailingstoploss' in config:
        if isinstance(config['trailingstoploss'], (int, str)):
            p = re.compile(r"^\-[0-9\.]{1,5}$")
            if isinstance(config['trailingstoploss'], str) and p.match(config['trailingstoploss']):
                app.trailing_stop_loss = float(config['trailingstoploss'])
            elif isinstance(config['trailingstoploss'], int) and config['trailingstoploss'] >= -100 and config['trailingstoploss'] < 0:
                app.trailing_stop_loss = float(config['trailingstoploss'])

    if 'autorestart' in config:
        if isinstance(config['autorestart'], int):
            if config['autorestart'] in [ 0, 1 ]:
                app.autorestart = bool(config['autorestart'])

    if 'sellatloss' in config:
        if isinstance(config['sellatloss'], int):
            if config['sellatloss'] in [ 0, 1 ]:
                app.sell_at_loss = config['sellatloss']
                if app.sell_at_loss == 0:
                    app.sell_lower_pcnt = None

    if 'sellatresistance' in config:
        if isinstance(config['sellatresistance'], int):
            if config['sellatresistance'] in [ 0, 1 ]:
                app.sellatresistance = bool(config['sellatresistance'])

    if 'disablebullonly' in config:
        if isinstance(config['disablebullonly'], int) and bool(config['disablebullonly']):
            app.disablebullonly = True

    if 'disablebuynearhigh' in config:
        if isinstance(config['disablebuynearhigh'], int) and bool(config['disablebuynearhigh']):
            app.disablebuynearhigh = True

    if 'disablebuymacd' in config:
        if isinstance(config['disablebuymacd'], int) and bool(config['disablebuymacd']):
            app.disablebuymacd = True

    if 'disablebuyobv' in config:
        if isinstance(config['disablebuyobv'], int) and bool(config['disablebuyobv']):
            app.disablebuyobv = True

    if 'disablebuyelderray' in config:
        if isinstance(config['disablebuyelderray'], int) and bool(config['disablebuyelderray']):
            app.disablebuyelderray = True

    if 'disablefailsafefibonaccilow' in config:
        if isinstance(config['disablefailsafefibonaccilow'], int) and bool(config['disablefailsafefibonaccilow']):
            app.disablefailsafefibonaccilow = True

    if 'disablefailsafelowerpcnt' in config:
        if isinstance(config['disablefailsafelowerpcnt'], int) and bool(config['disablefailsafelowerpcnt']):
            app.disablefailsafelowerpcnt = True

    if 'disableprofitbankupperpcnt' in config:
        if isinstance(config['disableprofitbankupperpcnt'], int) and bool(config['disableprofitbankupperpcnt']):
            app.disableprofitbankupperpcnt = True

    if 'disableprofitbankreversal' in config:
        if isinstance(config['disableprofitbankreversal'], int) and bool(config['disableprofitbankreversal']):
            app.disableprofitbankreversal = True

    if 'disabletelegram' in config:
        if isinstance(config['disabletelegram'], int) and bool(config['disabletelegram']):
            app.disabletelegram = True

    if 'disablelog' in config:
        if isinstance(config['disablelog'], int) and bool(config['disablelog']):
            app.disablelog = True

    if 'disabletracker' in config:
        if isinstance(config['disabletracker'], int) and bool(config['disabletracker']):
            app.disabletracker = True

    # backward compatibility
    if 'nosellatloss' in config:
        if isinstance(config['nosellatloss'], int):
            if config['nosellatloss'] in [ 0, 1 ]:
                app.sell_at_loss = int(not config['nosellatloss'])
                if app.sell_at_loss == 0:
                    app.sell_lower_pcnt = None
                    app.trailing_stop_loss = None

    if 'smartswitch' in config:
        if isinstance(config['smartswitch'], int):
            if config['smartswitch'] in [ 0, 1 ]:
                app.smart_switch = config['smartswitch']
                if app.smart_switch == 1:
                    app.smart_switch = 1
                else:
                    app.smart_switch = 0

    if 'buypercent' in config:
        if isinstance(config['buypercent'], int):
            if config['buypercent'] > 0 and config['buypercent'] <= 100:
                app.buypercent = config['buypercent']

    if 'sellpercent' in config:
        if isinstance(config['sellpercent'], int):
            if config['sellpercent'] > 0 and config['sellpercent'] <= 100:
                app.sellpercent = config['sellpercent']

    if 'lastaction' in config:
        if isinstance(config['lastaction'], str):
            if config['lastaction'] in [ 'BUY', 'SELL' ]:
                app.last_action = config['lastaction']

    if 'buymaxsize' in config:
        if isinstance(config['buymaxsize'], int):
            if config['buymaxsize'] > 0:
                app.buymaxsize = config['buymaxsize']
