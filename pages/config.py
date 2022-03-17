# from subprocess import call
from dash import dcc, html, Input, Output, callback, State
import dash_bootstrap_components as dbc
from models.telegram import Wrapper
from models.exchange import Granularity

tg_wrapper = Wrapper("config.json", "webgui")
# selected_pair = None
CONTENT_STYLE = {
    "margin-left": "0rem",
    "margin-right": "0rem",
    "padding": "0rem 1rem",
}
layout = html.Div(style=CONTENT_STYLE, children=
    [
        html.H4("Bot Config Generator", style={"textAlign": "left"}),
        html.B(),
        html.Div(id="save-change-message"),
        html.Div(
            dbc.Button(
                "Save Changes",
                id="save-changes",
                value="save",
                n_clicks=0,
                disabled=False,
            ),
            className="d-grid gap-2",
        ),
        html.H5("Exchanges"),
        html.Div(
            dbc.Card(
                dbc.CardBody(
                    dbc.RadioItems(
                        options=[
                            {"label": "Coinbase Pro", "value": "coinbasepro"},
                            {"label": "Binance", "value": "binance"},
                            {"label": "Kucoin", "value": "kucoin"},
                        ],
                        value=None,
                        id="exchange-selector",
                        inline=True,
                    )
                )
            )
        ),
        dbc.Accordion(
            children=dbc.AccordionItem(
                id="start-accordian",
                title="Indicator Options",
                class_name="justify-content-md-center",
                children=dbc.Card(
                    dbc.CardBody(
                        html.Div(
                            [
                                dbc.Checklist(
                                    options=[
                                        {"label": "Live Mode", "value": "live"},
                                        {
                                            "label": "Disable EMA",
                                            "value": "disablebuyema",
                                        },
                                        {
                                            "label": "Disable MACD",
                                            "value": "disablebuymacd",
                                        },
                                        {
                                            "label": "Disable OBV",
                                            "value": "disablebuyobv",
                                        },
                                        {
                                            "label": "Disable Elderray",
                                            "value": "disablebuyelderray",
                                        },
                                        {
                                            "label": "Disable Failsafe Fibonacci Low ",
                                            "value": "disablefailsafefibonaccilow",
                                        },
                                        {
                                            "label": "Disable Bull Only",
                                            "value": "disablebullonly",
                                        },
                                        {
                                            "label": "Disable Buy Near High",
                                            "value": "disablebuynearhigh",
                                        },
                                    ],
                                    value=0,
                                    id="switches-indicators",
                                    switch=True,
                                    inline=True,
                                ),
                            ]
                        ),
                    )
                ),
            ),
            start_collapsed=True,
        ),
        html.B(),
        dbc.Accordion(
            children=dbc.AccordionItem(
                id="start-accordian",
                title="Basic Selling Options",
                class_name="justify-content-md-center",
                children=dbc.Card(
                    dbc.CardBody(
                        html.Div(
                            [
                                dbc.Checklist(
                                    options=[
                                        {
                                            "label": "Sell at a Loss",
                                            "value": "sellatloss",
                                        },
                                        {
                                            "label": "Sell at Resistance",
                                            "value": "sellatresistance",
                                        },
                                        {
                                            "label": "Disable Profit Bank Reversal",
                                            "value": "disableprofitbankreversal",
                                        },
                                        {
                                            "label": "Sell Smart Switch",
                                            "value": "sellsmartswitch",
                                        },
                                    ],
                                    value=[1],
                                    id="switches-sell",
                                    switch=True,
                                    inline=True,
                                ),
                            ]
                        )
                    )
                ),
            ),
            start_collapsed=True,
        ),
        html.B(),
        dbc.Accordion(
            children=dbc.AccordionItem(
                id="start-accordian",
                title="Time Frame Options",
                class_name="justify-content-md-center",
                children=dbc.Card(
                    dbc.CardBody(
                        html.Div(
                            [
                                dbc.RadioItems(
                                    options=[
                                        {
                                            "label": "Smart-Switch Granularity",
                                            "value": "ss",
                                        },
                                        {"label": "Granularity 1 Min", "value": 60},
                                        {"label": "Granularity 5 Min", "value": 300},
                                        {"label": "Granularity 15 Min", "value": 900},
                                        {"label": "Granularity 1 HR", "value": 3600},
                                    ],
                                    value=[1],
                                    id="switches-granularity",
                                    # switch=True,
                                    inline=True,
                                ),
                            ]
                        ),
                    )
                ),
            ),
            start_collapsed=True,
        ),
        html.B(),
        dbc.Accordion(
            children=dbc.AccordionItem(
                id="start-accordian",
                title="Advanced Options",
                class_name="justify-content-md-center",
                children=[
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(
                                        html.Div(
                                            [
                                                dbc.Checklist(
                                                    options=[
                                                        {
                                                            "label": "Enable Buy Size",
                                                            "value": "buysize",
                                                        },
                                                    ],
                                                    value=[1],
                                                    id="switches-buysize",
                                                    switch=True,
                                                    inline=True,
                                                ),
                                                dbc.Label("Maximum Buy Amount"),
                                                html.B(),
                                                html.Div(
                                                    dbc.Input(
                                                        id="buy-max-size",
                                                        placeholder="maximum amount ... ",
                                                        type="number",
                                                    ),
                                                ),
                                                dbc.Label("Minimum Buy Amount"),
                                                html.B(),
                                                html.Div(
                                                    dbc.Input(
                                                        id="buy-min-size",
                                                        placeholder="minimum amount ... ",
                                                        type="number",
                                                    ),
                                                ),
                                            ]
                                        )
                                    )
                                ),
                            ),
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(
                                        html.Div(
                                            [
                                                dbc.Checklist(
                                                    options=[
                                                        {
                                                            "label": "Prevent Loss",
                                                            "value": "preventloss",
                                                        },
                                                    ],
                                                    value=[1],
                                                    id="switches-advsell",
                                                    switch=True,
                                                    inline=True,
                                                ),
                                                dbc.Label("Prevent Loss Trigger"),
                                                html.B(),
                                                html.Div(
                                                    dcc.Slider(
                                                        0,
                                                        10,
                                                        0.05,
                                                        value=0,
                                                        id="prevent-loss-trigger",
                                                        marks=None,
                                                        tooltip={
                                                            "placement": "left",
                                                            "always_visible": True,
                                                        },
                                                        disabled=True,
                                                    ),
                                                ),
                                                dbc.Label("Prevent Loss Margin"),
                                                html.B(),
                                                html.Div(
                                                    dcc.Slider(
                                                        -10,
                                                        10,
                                                        0.05,
                                                        value=0,
                                                        id="prevent-loss-margin",
                                                        marks=None,
                                                        tooltip={
                                                            "placement": "left",
                                                            "always_visible": True,
                                                        },
                                                        disabled=True,
                                                    ),
                                                ),
                                            ]
                                        )
                                    )
                                ),
                            ),
                            # html.B(),
                            dbc.Col(
                                dbc.Card(
                                    dbc.CardBody(
                                        html.Div(
                                            [
                                                # dbc.Label("Advance Selling Options"),
                                                dbc.Checklist(
                                                    options=[
                                                        {
                                                            "label": "Trailing Stop Loss",
                                                            "value": "trailingstoploss",
                                                        },
                                                    ],
                                                    value=[1],
                                                    id="switches-tsl",
                                                    switch=True,
                                                    inline=True,
                                                ),
                                                dbc.Label("Trailing Stop Loss Trigger"),
                                                html.B(),
                                                html.Div(
                                                    dcc.Slider(
                                                        0,
                                                        30,
                                                        0.05,
                                                        value=0,
                                                        id="trailing-stop-loss-trigger",
                                                        marks=None,
                                                        tooltip={
                                                            "placement": "left",
                                                            "always_visible": True,
                                                        },
                                                        disabled=True,
                                                    ),
                                                ),
                                                dbc.Label("Trailing Stop Loss Margin"),
                                                html.B(),
                                                html.Div(
                                                    dcc.Slider(
                                                        -10,
                                                        10,
                                                        0.05,
                                                        value=0,
                                                        id="trailing-stop-loss-margin",
                                                        marks=None,
                                                        tooltip={
                                                            "placement": "left",
                                                            "always_visible": True,
                                                        },
                                                        disabled=True,
                                                    ),
                                                ),
                                            ]
                                        )
                                    )
                                ),
                            ),
                        ]
                    ),
                ],
            ),
            start_collapsed=True,
        ),
        html.B(),
        dbc.Accordion(
            children=dbc.AccordionItem(
                id="start-accordian",
                title="Extra Options",
                class_name="justify-content-md-center",
                children=dbc.Card(
                    dbc.CardBody(
                        html.Div(
                            dbc.Checklist(
                                options=[
                                    {"label": "Auto Restart", "value": "autorestart"},
                                    {"label": "Verbose", "value": "verbose"},
                                    {
                                        "label": "Disable Telegram Messages",
                                        "value": "disabletelegram",
                                    },
                                    {
                                        "label": "Enable Telegram Control",
                                        "value": "enabletelegrambotcontrol",
                                    },
                                    {"label": "Websockets", "value": "websocket"},
                                    {
                                        "label": "Disable Bot Logs",
                                        "value": "disablelog",
                                    },
                                    {
                                        "label": "Enable Machine Learning Messages",
                                        "value": "enableml",
                                    },
                                ],
                                value=[1],
                                id="switches-extras",
                                switch=True,
                                inline=True,
                            )
                        )
                    )
                ),
            ),
            start_collapsed=True,
        ),
    ],
)


@callback(
    Output("save-change-message", "children"),
    Input("save-changes", "n_clicks"),
    State("exchange-selector", "value"),
    State("switches-indicators", "options"),
    State("switches-indicators", "value"),
)
def save_changes_switch(value, exchange, ind_options, ind_value):
    """Save changes"""
    if value > 0:
        for option in ind_options:
            tg_wrapper.helper.config[exchange]["config"].update(
                {option["value"]: 1 if option["value"] in ind_value else 0}
            )
        return dbc.Alert(f"{exchange} changes saved successfully!", color="success", dismissable=True)

@callback(
    Output("buy-max-size", "disabled"),
    Output("buy-min-size", "disabled"),
    Input("switches-buysize", "value"),
)
def buy_size_switch(value):
    """enable/disable buy size amount"""
    if "buysize" in value:
        return False, False
    return True, True


@callback(
    Output("prevent-loss-trigger", "disabled"),
    Output("prevent-loss-margin", "disabled"),
    Input("switches-advsell", "value"),
)
def prevent_loss_switch(value):
    """enable/disable prevent loss settings"""
    if "preventloss" in value:
        return False, False
    return True, True


@callback(
    Output("trailing-stop-loss-trigger", "disabled"),
    Output("trailing-stop-loss-margin", "disabled"),
    Input("switches-tsl", "value"),
)
def trailing_stop_loss_switch(value):
    """enable/disable trailing stop loss settings"""
    if "trailingstoploss" in value:
        return False, False
    return True, True


@callback(
    [
        Output("switches-indicators", "value"),
        Output("switches-sell", "value"),
        Output("switches-advsell", "value"),
        Output("switches-tsl", "value"),
        Output("switches-extras", "value"),
        Output("switches-buysize", "value"),
    ],
    Input("exchange-selector", "value"),
)
def exchange_selector(value):
    """Select Exchange"""
    enabled_list = []
    if value is not None:
        if value in tg_wrapper.helper.config:
            for param in tg_wrapper.helper.config[value]["config"]:
                if tg_wrapper.helper.config[value]["config"][param] == 1:
                    enabled_list.append(param)

            if (
                "trailingstoplosstrigger" in tg_wrapper.helper.config[value]["config"]
                and "trailingstoploss" in tg_wrapper.helper.config[value]["config"]
            ):
                enabled_list.append("trailingstoploss")

            if (
                "buymaxsize" in tg_wrapper.helper.config[value]["config"]
                or "buyminsize" in tg_wrapper.helper.config[value]["config"]
            ):
                enabled_list.append("buysize")

    return (
        enabled_list,
        enabled_list,
        enabled_list,
        enabled_list,
        enabled_list,
        enabled_list,
    )


@callback(
    Output("buy-max-size", "value"),
    Input("exchange-selector", "value"),
)
def buy_max_size(value):
    result = ""
    if value is not None:
        if value in tg_wrapper.helper.config:
            if "buymaxsize" in tg_wrapper.helper.config[value]["config"]:
                result = tg_wrapper.helper.config[value]["config"]["buymaxsize"]
    return result


@callback(
    Output("buy-min-size", "value"),
    Input("exchange-selector", "value"),
)
def buy_min_size(value):
    result = ""
    if value is not None:
        if value in tg_wrapper.helper.config:
            if "buyminsize" in tg_wrapper.helper.config[value]["config"]:
                result = tg_wrapper.helper.config[value]["config"]["buyminsize"]
    return result


@callback(
    Output("switches-granularity", "value"),
    Input("exchange-selector", "value"),
)
def granularity_selector(value):
    """read granularityfrom config"""
    granularity = "ss"
    if value is not None:
        if value in tg_wrapper.helper.config:
            if "granularity" in tg_wrapper.helper.config[value]["config"]:
                granularity = Granularity.Granularity.convert_to_enum(
                    tg_wrapper.helper.config[value]["config"]["granularity"]
                ).to_integer

    return granularity


@callback(
    Output("trailing-stop-loss-trigger", "value"),
    Output("trailing-stop-loss-margin", "value"),
    Input("exchange-selector", "value"),
)
def trailing_stop_loss_trigger(value):
    """read trailingstoplosstrigger from config"""
    tsl_trigger = 0
    tsl_margin = 0
    if value is not None:
        if value in tg_wrapper.helper.config:
            if "trailingstoplosstrigger" in tg_wrapper.helper.config[value]["config"]:
                tsl_trigger = tg_wrapper.helper.config[value]["config"][
                    "trailingstoplosstrigger"
                ]
            if "trailingstoploss" in tg_wrapper.helper.config[value]["config"]:
                tsl_margin = tg_wrapper.helper.config[value]["config"][
                    "trailingstoploss"
                ]

    return tsl_trigger, tsl_margin


@callback(
    Output("prevent-loss-trigger", "value"),
    Output("prevent-loss-margin", "value"),
    Input("exchange-selector", "value"),
)
def prevent_loss_trigger(value):
    """read preventloss from config"""
    pl_trigger = 0
    pl_margin = 0
    if value is not None:
        if value in tg_wrapper.helper.config:
            if "preventlosstrigger" in tg_wrapper.helper.config[value]["config"]:
                pl_trigger = tg_wrapper.helper.config[value]["config"][
                    "preventlosstrigger"
                ]
            if "preventlossmargin" in tg_wrapper.helper.config[value]["config"]:
                pl_margin = tg_wrapper.helper.config[value]["config"][
                    "preventlossmargin"
                ]

    return pl_trigger, pl_margin


@callback(
    Output("switches-indicators", "visible"),
    Input("switches-indicators", "value"),
    Input("switches-sell", "value"),
    State("exchange-selector", "value"),
    State("switches-indicators", "options"),
    State("switches-sell", "options"),
)
def switched(enabled_list, sell_list, exchange, options, sell_options):
    """Make config changes"""
    if exchange is not None:
        if exchange in tg_wrapper.helper.config:
            config_list = tg_wrapper.helper.config[exchange]
        else:
            config_list = {exchange: {"config": {}}}
        for option in options:
            if option["value"] in enabled_list:
                if exchange in tg_wrapper.helper.config:
                    tg_wrapper.helper.config[exchange]["config"][option["value"]] = 1
                config_list[exchange]["config"].update({option["value"]: 1})
            else:
                if exchange in tg_wrapper.helper.config:
                    tg_wrapper.helper.config[exchange]["config"][option["value"]] = 0
                config_list[exchange]["config"].update({option["value"]: 0})

        for option in sell_options:
            if option["value"] in sell_list:
                if exchange in tg_wrapper.helper.config:
                    tg_wrapper.helper.config[exchange]["config"][option["value"]] = 1
                config_list[exchange]["config"].update({option["value"]: 1})
            else:
                if exchange in tg_wrapper.helper.config:
                    tg_wrapper.helper.config[exchange]["config"][option["value"]] = 0
                config_list[exchange]["config"].update({option["value"]: 0})

        tg_wrapper.helper.config.update(config_list)
        print(tg_wrapper.helper.config[exchange])
        return True
    else:
        return True


@callback(
    Output("switches-granularity", "visible"),
    Input("switches-granularity", "value"),
    State("exchange-selector", "value"),
)
def switch_granularity(gran, exchange):
    """Set exchange granularity"""
    if exchange is not None and gran != "":
        if gran == "ss":
            tg_wrapper.helper.config[exchange]["config"].pop("granularity")
        else:
            gran = Granularity.Granularity.convert_to_enum(gran)

            if exchange == "coinbasepro":
                tg_wrapper.helper.config[exchange]["config"].update(
                    {"granularity": gran.to_integer}
                )
            if exchange == "binance":
                tg_wrapper.helper.config[exchange]["config"].update(
                    {"granularity": gran.to_medium}
                )
            if exchange == "kucoin":
                tg_wrapper.helper.config[exchange]["config"].update(
                    {"granularity": gran.to_short}
                )

    return True
