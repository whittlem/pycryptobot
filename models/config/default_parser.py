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
        else:
            raise TypeError('live must be of type int')

    if 'verbose' in config:
        if isinstance(config['verbose'], int):
            if config['verbose'] in [0, 1]:
                app.is_verbose = config['verbose']
        else:
            raise TypeError('verbose must be of type int')

    if 'graphs' in config:
        if isinstance(config['graphs'], int):
            if config['graphs'] in [0, 1]:
                app.save_graphs = config['graphs']
        else:
            raise TypeError('graphs must be of type int')

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
                if 'simenddate' in config:
                    app.simenddate = config['simenddate']
        else:
            raise TypeError('sim must be of type str')

    if 'sellupperpcnt' in config:
        if isinstance(config['sellupperpcnt'], (int, float, str)):
            p = re.compile(r"^\-*[0-9\.]{1,5}$")
            if isinstance(config['sellupperpcnt'], str) and p.match(config['sellupperpcnt']):
                if float(config['sellupperpcnt']) > 0:
                    app.sell_upper_pcnt = float(config['sellupperpcnt'])
                else:
                    raise ValueError('sellupperpcnt must be positive')
            elif isinstance(config['sellupperpcnt'], (int, float)) and config['sellupperpcnt'] >= 0 and config['sellupperpcnt'] <= 100:
                if float(config['sellupperpcnt']) > 0:
                    app.sell_upper_pcnt = float(config['sellupperpcnt'])
                else:
                    raise ValueError('sellupperpcnt must be positive')
            elif isinstance(config['sellupperpcnt'], (int, float)) and config['sellupperpcnt'] < 0:
                raise ValueError('sellupperpcnt must be positive')
        else:
            raise TypeError('sellupperpcnt must be of type int or str')

    if 'selllowerpcnt' in config:
        if isinstance(config['selllowerpcnt'], (int, float, str)):
            p = re.compile(r"^\-*[0-9\.]{1,5}$")
            if isinstance(config['selllowerpcnt'], str) and p.match(config['selllowerpcnt']):
                if float(config['selllowerpcnt']) < 0:
                    app.sell_lower_pcnt  = float(config['selllowerpcnt'])
                else:
                    raise ValueError('selllowerpcnt must be negative')
            elif isinstance(config['selllowerpcnt'], (int, float)) and config['selllowerpcnt'] >= -100 and config['selllowerpcnt'] <= 0:
                if float(config['selllowerpcnt']) < 0:
                    app.sell_lower_pcnt  = float(config['selllowerpcnt'])
                else:
                    raise ValueError('selllowerpcnt must be negative')
            elif isinstance(config['selllowerpcnt'], (int, float)) and config['selllowerpcnt'] >= 0:
                raise ValueError('selllowerpcnt must be negative')
        else:
            raise TypeError('selllowerpcnt must be of type int or str')

    if 'trailingstoploss' in config:
        if isinstance(config['trailingstoploss'], (int, float, str)):
            p = re.compile(r"^\-*[0-9\.]{1,5}$")
            if isinstance(config['trailingstoploss'], str) and p.match(config['trailingstoploss']):
                if float(config['trailingstoploss']) < 0:
                    app.trailing_stop_loss  = float(config['trailingstoploss'])
                else:
                    raise ValueError('trailingstoploss must be negative')
            elif isinstance(config['trailingstoploss'], (int, float)) and config['trailingstoploss'] >= -100 and config['trailingstoploss'] <= 0:
                if float(config['trailingstoploss']) < 0:
                    app.trailing_stop_loss  = float(config['trailingstoploss'])
                else:
                    raise ValueError('trailingstoploss must be negative')
            elif isinstance(config['trailingstoploss'], (int, float)) and config['trailingstoploss'] >= 0:
                raise ValueError('trailingstoploss must be negative')
        else:
            raise TypeError('trailingstoploss must be of type int or str')

    if 'autorestart' in config:
        if isinstance(config['autorestart'], int):
            if config['autorestart'] in [ 0, 1 ]:
                app.autorestart = bool(config['autorestart'])
        else:
            raise TypeError('autorestart must be of type int')

    if 'sellatloss' in config:
        if isinstance(config['sellatloss'], int):
            if config['sellatloss'] in [ 0, 1 ]:
                app.sell_at_loss = config['sellatloss']
                if app.sell_at_loss == 0:
                    app.sell_lower_pcnt = None
        else:
            raise TypeError('sellatloss must be of type int')

    if 'sellatresistance' in config:
        if isinstance(config['sellatresistance'], int):
            if config['sellatresistance'] in [ 0, 1 ]:
                app.sellatresistance = bool(config['sellatresistance'])
        else:
            raise TypeError('sellatresistance must be of type int')

    if 'disablebullonly' in config:
        if isinstance(config['disablebullonly'], int):
            if bool(config['disablebullonly']):
                app.disablebullonly = True
        else:
            raise TypeError('disablebullonly must be of type int')

    if 'disablebuynearhigh' in config:
        if isinstance(config['disablebuynearhigh'], int):
            if bool(config['disablebuynearhigh']):
                app.disablebuynearhigh = True
        else:
            raise TypeError('disablebuynearhigh must be of type int')

    if 'disablebuymacd' in config:
        if isinstance(config['disablebuymacd'], int):
            if bool(config['disablebuymacd']):
                app.disablebuymacd = True
        else:
            raise TypeError('disablebuymacd must be of type int')

    if 'disablebuyobv' in config:
        if isinstance(config['disablebuyobv'], int):
            if bool(config['disablebuyobv']):
                app.disablebuyobv = True
        else:
            raise TypeError('disablebuyobv must be of type int')

    if 'disablebuyelderray' in config:
        if isinstance(config['disablebuyelderray'], int):
            if bool(config['disablebuyelderray']):
                app.disablebuyelderray = True
        else:
            raise TypeError('disablebuyelderray must be of type int')

    if 'disablefailsafefibonaccilow' in config:
        if isinstance(config['disablefailsafefibonaccilow'], int):
            if bool(config['disablefailsafefibonaccilow']):
                app.disablefailsafefibonaccilow = True
        else:
            raise TypeError('disablefailsafefibonaccilow must be of type int')

    if 'disablefailsafelowerpcnt' in config:
        if isinstance(config['disablefailsafelowerpcnt'], int):
            if bool(config['disablefailsafelowerpcnt']):
                app.disablefailsafelowerpcnt = True
        else:
            raise TypeError('disablefailsafelowerpcnt must be of type int')

    if 'disableprofitbankupperpcnt' in config:
        if isinstance(config['disableprofitbankupperpcnt'], int):
            if bool(config['disableprofitbankupperpcnt']):
                app.disableprofitbankupperpcnt = True
        else:
            raise TypeError('disableprofitbankupperpcnt must be of type int')

    if 'disableprofitbankreversal' in config:
        if isinstance(config['disableprofitbankreversal'], int):
            if bool(config['disableprofitbankreversal']):
                app.disableprofitbankreversal = True
        else:
            raise TypeError('disableprofitbankreversal must be of type int')

    if 'disabletelegram' in config:
        if isinstance(config['disabletelegram'], int):
            if bool(config['disabletelegram']):
                app.disabletelegram = True
        else:
            raise TypeError('disabletelegram must be of type int')

    if 'disablelog' in config:
        if isinstance(config['disablelog'], int):
            if bool(config['disablelog']):
                app.disablelog = True
        else:
            raise TypeError('disablelog must be of type int')

    if 'disabletracker' in config:
        if isinstance(config['disabletracker'], int):
            if bool(config['disabletracker']):
                app.disabletracker = True
        else:
            raise TypeError('disabletracker must be of type int')

    # backward compatibility
    if 'nosellatloss' in config:
        if isinstance(config['nosellatloss'], int):
            if config['nosellatloss'] in [ 0, 1 ]:
                app.sell_at_loss = int(not config['nosellatloss'])
                if app.sell_at_loss == 0:
                    app.sell_lower_pcnt = None
                    app.trailing_stop_loss = None
        else:
            raise TypeError('nosellatloss must be of type int')

    if 'smartswitch' in config:
        if isinstance(config['smartswitch'], int):
            if config['smartswitch'] in [ 0, 1 ]:
                app.smart_switch = config['smartswitch']
                if app.smart_switch == 1:
                    app.smart_switch = 1
                else:
                    app.smart_switch = 0
        else:
            raise TypeError('smartswitch must be of type int')

    if 'buypercent' in config:
        if isinstance(config['buypercent'], int):
            if config['buypercent'] > 0 and config['buypercent'] <= 100:
                app.buypercent = config['buypercent']
        else:
            raise TypeError('buypercent must be of type int')

    if 'sellpercent' in config:
        if isinstance(config['sellpercent'], int):
            if config['sellpercent'] > 0 and config['sellpercent'] <= 100:
                app.sellpercent = config['sellpercent']
        else:
            raise TypeError('sellpercent must be of type int')

    if 'lastaction' in config:
        if isinstance(config['lastaction'], str):
            if config['lastaction'] in [ 'BUY', 'SELL' ]:
                app.last_action = config['lastaction']
        else:
            raise TypeError('lastaction must be of type str')

    if 'buymaxsize' in config:
        if isinstance(config['buymaxsize'], (int, float)):
            if config['buymaxsize'] > 0:
                app.buymaxsize = config['buymaxsize']
        else:
            raise TypeError('buymaxsize must be of type int or float')