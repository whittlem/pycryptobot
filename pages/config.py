# from subprocess import call
from dash import dcc, html, Input, Output, callback, State
import dash_bootstrap_components as dbc
from models.telegram import Wrapper
from models.exchange import Granularity

tg_wrapper = Wrapper("config.json", "webgui")
tg_wrapper.helper.read_config()
# selected_pair = None
CONTENT_STYLE = {
    "margin-left": "0rem",
    "margin-right": "0rem",
    "padding": "0rem 1rem",
}
layout = (
    html.Div(
        style=CONTENT_STYLE,
        children=[
            html.H4("Bot Config Generator", style={"textAlign": "left"}),
            html.B(),
            html.Div(id="save-change-message"),
            html.Div(
                dbc.Button(
                    "Save Changes",
                    id="save-changes",
                    value="saved",
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
            dbc.Card(
                dbc.CardBody(
                    html.Div(
                        [
                            dbc.Label("Advance Selling Options"),
                            dbc.Checklist(
                                options=[
                                    {
                                        "label": "Trailing Immediate Buy",
                                        "value": "Trailing Immediate Buy",
                                    },
                                    {"label": "Prevent Loss", "value": "Prevent Loss"},
                                ],
                                value=[1],
                                id="switches-advsell",
                                switch=True,
                                inline=True,
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
                                                            {
                                                                "label": "Granularity 1 Min",
                                                                "value": 60,
                                                            },
                                                            {
                                                                "label": "Granularity 5 Min",
                                                                "value": 300,
                                                            },
                                                            {
                                                                "label": "Granularity 15 Min",
                                                                "value": 900,
                                                            },
                                                            {
                                                                "label": "Granularity 1 HR",
                                                                "value": 3600,
                                                            },
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
                                                                    dbc.Label(
                                                                        "Maximum Buy Amount"
                                                                    ),
                                                                    html.B(),
                                                                    html.Div(
                                                                        dbc.Input(
                                                                            id="buy-max-size",
                                                                            placeholder="maximum amount ... ",
                                                                            type="number",
                                                                        ),
                                                                    ),
                                                                    dbc.Label(
                                                                        "Minimum Buy Amount"
                                                                    ),
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
                                                    xs=12,
                                                    md=6,
                                                    lg=4,
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
                                                                        id="switches-preventloss",
                                                                        switch=True,
                                                                        inline=True,
                                                                    ),
                                                                    dbc.Label(
                                                                        "Prevent Loss Trigger"
                                                                    ),
                                                                    html.B(),
                                                                    html.Div(
                                                                        dcc.Slider(
                                                                            0,
                                                                            10,
                                                                            0.1,
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
                                                                    dbc.Label(
                                                                        "Prevent Loss Margin"
                                                                    ),
                                                                    html.B(),
                                                                    html.Div(
                                                                        dcc.Slider(
                                                                            -10,
                                                                            0,
                                                                            0.5,
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
                                                    xs=12,
                                                    md=6,
                                                    lg=4,
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
                                                                    dbc.Label(
                                                                        "Trailing Stop Loss Trigger"
                                                                    ),
                                                                    html.B(),
                                                                    html.Div(
                                                                        dcc.Slider(
                                                                            0,
                                                                            30,
                                                                            0.1,
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
                                                                    dbc.Label(
                                                                        "Trailing Stop Loss Margin"
                                                                    ),
                                                                    html.B(),
                                                                    html.Div(
                                                                        dcc.Slider(
                                                                            -10,
                                                                            0,
                                                                            0.5,
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
                                                    xs=12,
                                                    md=6,
                                                    lg=4,
                                                ),
                                                dbc.Col(
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            html.Div(
                                                                [
                                                                    dbc.Checklist(
                                                                        options=[
                                                                            {
                                                                                "label": "Disable Buy Near High Default",
                                                                                "value": "disablebuynearhigh",
                                                                            },
                                                                        ],
                                                                        value=[1],
                                                                        id="switches-buynearhigh",
                                                                        switch=True,
                                                                        inline=True,
                                                                    ),
                                                                    dbc.Label(
                                                                        "(Optional) No Buy Near High %"
                                                                    ),
                                                                    html.B(),
                                                                    html.Div(
                                                                        dbc.Input(
                                                                            id="buy-near-high",
                                                                            placeholder="no buy near high ... ",
                                                                            type="number",
                                                                        ),
                                                                    ),
                                                                ]
                                                            )
                                                        )
                                                    ),
                                                    xs=12,
                                                    md=6,
                                                    lg=4,
                                                ),
                                                dbc.Col(
                                                    dbc.Card(
                                                        dbc.CardBody(
                                                            html.Div(
                                                                [
                                                                    dbc.Checklist(
                                                                        options=[
                                                                            {
                                                                                "label": "Enable Sell At Loss",
                                                                                "value": "sellatloss",
                                                                            },
                                                                        ],
                                                                        value=[1],
                                                                        id="switches-sellatloss",
                                                                        switch=True,
                                                                        inline=True,
                                                                    ),
                                                                    dbc.Label(
                                                                        "Ignore Sell Triggers until (%)"
                                                                    ),
                                                                    html.B(),
                                                                    html.Div(
                                                                        dcc.Slider(
                                                                            -10,
                                                                            0,
                                                                            0.1,
                                                                            value=0,
                                                                            id="sell-at-loss-trigger",
                                                                            marks=None,
                                                                            tooltip={
                                                                                "placement": "left",
                                                                                "always_visible": True,
                                                                            },
                                                                            disabled=True,
                                                                        ),
                                                                    ),
                                                                    dbc.Label(
                                                                        "FailSafe sell point (%)"
                                                                    ),
                                                                    html.B(),
                                                                    html.Div(
                                                                        dcc.Slider(
                                                                            -25,
                                                                            2,
                                                                            0.5,
                                                                            value=0,
                                                                            id="sell-at-loss-margin",
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
                                                    xs=12,
                                                    md=6,
                                                    lg=4,
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
                                                        {
                                                            "label": "Auto Restart",
                                                            "value": "autorestart",
                                                        },
                                                        {
                                                            "label": "Verbose",
                                                            "value": "verbose",
                                                        },
                                                        {
                                                            "label": "Disable Telegram Messages",
                                                            "value": "disabletelegram",
                                                        },
                                                        {
                                                            "label": "Enable Telegram Control",
                                                            "value": "enabletelegrambotcontrol",
                                                        },
                                                        {
                                                            "label": "Websockets",
                                                            "value": "websocket",
                                                        },
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
                )
            ),
        ],
    ),
)


@callback(
    Output("save-change-message", "children"),
    Input("save-changes", "n_clicks"),
    State("exchange-selector", "value"),
    State("switches-buysize", "value"),
    State("buy-max-size", "value"),
    State("buy-min-size", "value"),
    State("switches-preventloss", "value"),
    State("prevent-loss-trigger", "value"),
    State("prevent-loss-margin", "value"),
    State("switches-tsl", "value"),
    State("trailing-stop-loss-trigger", "value"),
    State("trailing-stop-loss-margin", "value"),
    State("switches-buynearhigh", "value"),
    State("buy-near-high", "value"),
    State("switches-sellatloss", "value"),
    State("sell-at-loss-trigger", "value"),
    State("sell-at-loss-margin", "value"),
)
def save_changes_buysize(
    value,
    exchange,
    buysize,
    buymaxsize,
    buyminsize,
    preventloss,
    pl_trigger,
    pl_margin,
    tsl,
    tsl_trigger,
    tsl_margin,
    buynearhigh,
    buynearhigh_percent,
    sellatloss,
    nosellminpcnt,
    selllowerpcnt,
):
    """Save changes"""
    if value > 0:
        if "buysize" in buysize:
            tg_wrapper.helper.config[exchange]["config"].update(
                {"buymaxsize": buymaxsize}
            )
            tg_wrapper.helper.config[exchange]["config"].update(
                {"buyminsize": buyminsize}
            )
        else:
            if "buymaxsize" in tg_wrapper.helper.config[exchange]["config"]:
                tg_wrapper.helper.config[exchange]["config"].pop("buymaxsize")
            if "buyminsize" in tg_wrapper.helper.config[exchange]["config"]:
                tg_wrapper.helper.config[exchange]["config"].pop("buyminsize")

        if "preventloss" in preventloss:
            tg_wrapper.helper.config[exchange]["config"].update(
                {"preventlosstrigger": pl_trigger}
            )
            tg_wrapper.helper.config[exchange]["config"].update(
                {"preventlossmargin": pl_margin}
            )

        if "trailingstoploss" in tsl:
            tg_wrapper.helper.config[exchange]["config"].update(
                {"trailingstoplosstrigger": tsl_trigger}
            )
            tg_wrapper.helper.config[exchange]["config"].update(
                {"trailingstoploss": tsl_margin}
            )
        else:
            if (
                "trailingstoplosstrigger"
                in tg_wrapper.helper.config[exchange]["config"]
            ):
                tg_wrapper.helper.config[exchange]["config"].pop(
                    "trailingstoplosstrigger"
                )
            if "trailingstoploss" in tg_wrapper.helper.config[exchange]["config"]:
                tg_wrapper.helper.config[exchange]["config"].pop("trailingstoploss")

        if "disablebuynearhigh" in buynearhigh:
            tg_wrapper.helper.config[exchange]["config"].update(
                {"disablebuynearhigh": 1}
            )
            tg_wrapper.helper.config[exchange]["config"].update(
                {"nobuynearhighpcnt": buynearhigh_percent}
            )
        else:
            if "disablebuynearhigh" in tg_wrapper.helper.config[exchange]["config"]:
                tg_wrapper.helper.config[exchange]["config"].pop("disablebuynearhigh")
            if "nobuynearhighpcnt" in tg_wrapper.helper.config[exchange]["config"]:
                tg_wrapper.helper.config[exchange]["config"].pop("nobuynearhighpcnt")

        if "sellatloss" in sellatloss:
            tg_wrapper.helper.config[exchange]["config"].update(
                {"nosellminpcnt": nosellminpcnt}
            )
            tg_wrapper.helper.config[exchange]["config"].update(
                {"selllowerpcnt": selllowerpcnt}
            )
        # else:
        #     if "nosellminpcnt" in tg_wrapper.helper.config[exchange]["config"]:
        #         tg_wrapper.helper.config[exchange]["config"].pop("nosellminpcnt")
        #     if "selllowerpcnt" in tg_wrapper.helper.config[exchange]["config"]:
        #         tg_wrapper.helper.config[exchange]["config"].pop("selllowerpcnt")

        if tg_wrapper.helper.write_config():
            return dbc.Alert(
                "Config File Update - SUCCESS", color="success", dismissable=True
            )

        return dbc.Alert(
            "Config File Update - FAILED", color="danger", dismissable=True
        )


@callback(
    Output("sell-at-loss-trigger", "disabled"),
    Output("sell-at-loss-margin", "disabled"),
    Input("switches-sellatloss", "value"),
    State("exchange-selector", "value"),
)
def sell_at_loss_switch(value, exchange):
    """enable/disable buy size amount"""
    tg_wrapper.helper.config[exchange]["config"].update({"sellatloss": 0})
    if "sellatloss" in value:
        tg_wrapper.helper.config[exchange]["config"].update({"sellatloss": 1})
        return False, False
    return True, True


@callback(
    Output("buy-near-high", "disabled"),
    Input("switches-buynearhigh", "value"),
)
def buy_near_high_switch(value):
    """enable/disable buy size amount"""
    if "disablebuynearhigh" in value:
        return False
    return True


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
    Input("switches-preventloss", "value"),
    State("exchange-selector", "value"),
)
def prevent_loss_switch(value, exchange):
    """enable/disable prevent loss settings"""
    tg_wrapper.helper.config[exchange]["config"].update({"preventloss": 0})
    if "preventloss" in value:
        tg_wrapper.helper.config[exchange]["config"].update({"preventloss": 1})
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
        Output("switches-preventloss", "value"),
        Output("switches-tsl", "value"),
        Output("switches-extras", "value"),
        Output("switches-buysize", "value"),
        Output("switches-buynearhigh", "value"),
        Output("switches-sellatloss", "value"),
    ],
    Input("exchange-selector", "value"),
)
def exchange_selector(value):
    """Select Exchange"""
    enabled_list = []
    tg_wrapper.helper.read_config()
    if value is not None:
        if value not in tg_wrapper.helper.config:
            tg_wrapper.helper.config.update({value: {"config": {}}})
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
        enabled_list,
        enabled_list,
    )


@callback(
    Output("sell-at-loss-trigger", "value"),
    Output("sell-at-loss-margin", "value"),
    Input("exchange-selector", "value"),
)
def sell_at_loss(value):
    result = 0
    margin = 0
    if value is not None:
        if value in tg_wrapper.helper.config:
            if "nosellminpcnt" in tg_wrapper.helper.config[value]["config"]:
                result = tg_wrapper.helper.config[value]["config"]["nosellminpcnt"]
            if "selllowerpcnt" in tg_wrapper.helper.config[value]["config"]:
                margin = tg_wrapper.helper.config[value]["config"]["selllowerpcnt"]
    return result, margin


@callback(
    Output("buy-near-high", "value"),
    Input("exchange-selector", "value"),
)
def buy_near_high(value):
    result = 0
    if value is not None:
        if value in tg_wrapper.helper.config:
            if "nobuynearhighpcnt" in tg_wrapper.helper.config[value]["config"]:
                result = tg_wrapper.helper.config[value]["config"]["nobuynearhighpcnt"]
    return result


@callback(
    Output("buy-max-size", "value"),
    Input("exchange-selector", "value"),
)
def buy_max_size(value):
    result = 0
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
    result = 0
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
    Input("switches-extras", "value"),
    State("exchange-selector", "value"),
    State("switches-indicators", "options"),
    State("switches-sell", "options"),
    State("switches-extras", "options"),
)
def switched(
    enabled_list,
    sell_list,
    options_list,
    exchange,
    options,
    sell_options,
    extras_options,
):
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
                config_list["config"].update({option["value"]: 1})
            else:
                if exchange in tg_wrapper.helper.config:
                    tg_wrapper.helper.config[exchange]["config"][option["value"]] = 0
                config_list["config"].update({option["value"]: 0})

        for option in sell_options:
            if option["value"] in sell_list:
                if exchange in tg_wrapper.helper.config:
                    tg_wrapper.helper.config[exchange]["config"][option["value"]] = 1
                config_list["config"].update({option["value"]: 1})
            else:
                if exchange in tg_wrapper.helper.config:
                    tg_wrapper.helper.config[exchange]["config"][option["value"]] = 0
                config_list["config"].update({option["value"]: 0})

        for option in extras_options:
            if option["value"] in options_list:
                if exchange in tg_wrapper.helper.config:
                    tg_wrapper.helper.config[exchange]["config"][option["value"]] = 1
                config_list["config"].update({option["value"]: 1})
            else:
                if exchange in tg_wrapper.helper.config:
                    tg_wrapper.helper.config[exchange]["config"][option["value"]] = 0
                config_list["config"].update({option["value"]: 0})

        tg_wrapper.helper.config[exchange].update(config_list)
        print(tg_wrapper.helper.config[exchange]["config"])
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
