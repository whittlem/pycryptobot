""" WebGui Bot Controls """
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, MATCH, callback

from models.telegram import Wrapper

tg_wrapper = Wrapper("config.json")
selected_pair = None

tg_wrapper.helper.clean_data_folder()
def update_buttons(pair, value):
    """show/hide control buttons"""
    if pair is not None:
        tg_wrapper.helper.read_data(pair)
        if "margin" in tg_wrapper.helper.data:
            if value == "":
                return tg_wrapper.helper.data["margin"] != " "
            else:
                return tg_wrapper.helper.data["margin"] == value
    return "false"


def get_bot_status(pair):
    if pair is not None:
        return f"Uptime: {tg_wrapper.helper.get_uptime()} - Status: {tg_wrapper.helper.data['botcontrol']['status']} - Margin: {tg_wrapper.helper.data['margin']}"


layout = html.Div(
    [
        ### html buttons
        html.P(),
        html.H4("Controls", style={"textAlign": "left"}),
        html.H5("Main", style={"textAlign": "left"}),
        html.Button(
            "Restart Open Orders",
            id="btn-open-orders",
            n_clicks=0,
            className="btn btn-primary",
        ),
        html.P(),
        html.Button(
            "Market Scanning",
            id="btn-start-scanning",
            n_clicks=0,
            className="btn btn-primary",
        ),
        dbc.Collapse(
            dbc.Card(
                dbc.CardBody(
                    html.Div(id="market-scan-options"),
                )
            ),
            id="scan_options",
            is_open=False,
        ),
        # html.Div(id='market-scan-options'),
        html.P(),
        # html.H5("Manual Start Bot List", style={"textAlign": "left"}),
        dbc.Accordion(
            children=dbc.AccordionItem(
                id="start-accordian",
                title="Manual Start Bot List",
                class_name="justify-content-md-center",
            ),
            start_collapsed=True,
        ),
        html.P(),
        # html.Div(id="start-accordian"),
        # html.H5("Bot specific controls", style={"textAlign": "left"}),
        dbc.Accordion(
            children=dbc.AccordionItem(
                id="bot-accordian",
                title="Bot Controls",
                class_name="justify-content-md-center",
            ),
            start_collapsed=True,
        ),
        html.P(),
        # html.Div(id="bot-accordian"),
        # html.Div(id="container-button-timestamp"),
        dcc.Interval(id="interval-container", interval=30000, n_intervals=0),
        # html.Div(id="dummy-div-0"),
        # html.Div(id="dummy-div-1"),
        # html.Div(id="dummy-div-2"),
        # html.Div(id="dummy-div-3"),
        # html.Div(id="dummy-div-4"),
        # html.Div(id="dummy-div-5"),
        # html.Div(id="dummy-div-6"),
        # html.Div(id="dummy-div-7"),
    ],
    className="d-grid gap-2 col-11 mx-auto",
)
scan_layout = html.Div(
    className="d-grid gap-2 col-6 mx-auto",
    children=[
        html.P(),
        html.H5("Options", style={"textAlign": "left"}),
        # html.Div(id="schedule",className="d-grid gap-2 col-12 mx-auto"),
        html.P(),
        # html.Button(
        #     "Scan Only", id="btn-scan-only", n_clicks=0, className="btn btn-primary"
        # ),
        # html.Button(
        #     "Start Bots Only",
        #     id="btn-start-only",
        #     n_clicks=0,
        #     className="btn btn-primary",
        # ),
        # html.P(),
        # html.Button(
        #     "Scan and Start Bots",
        #     id="btn-scan-start",
        #     n_clicks=0,
        #     className="btn btn-primary",
        # ),
        # html.P(),
    ],
)

scan_layoutv2 = html.Div(
    [
        dbc.Row(
            dbc.Col(
                html.Div(
                    html.H5("Options", style={"textAlign": "center"}),
                    className="d-grid gap-2",
                ),
                width={"size": 6, "offset": 3},
            )
        ),
        dbc.Row(
            dbc.Col(
                html.Div(
                    id="schedule",
                    className="d-grid gap-2",
                ),
                width={"size": 6, "offset": 3},
            )
        ),
        html.P(),
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        html.Button(
                            "Scan Only",
                            id="btn-scan-only",
                            n_clicks=0,
                            className="btn btn-primary",
                        ),
                        className="d-grid gap-2",
                    ),
                    width={"size": 4, "offset": 2},
                ),
                dbc.Col(
                    html.Div(
                        html.Button(
                            "Start Bots Only",
                            id="btn-start-only",
                            n_clicks=0,
                            className="btn btn-primary",
                        ),
                        className="d-grid gap-2",
                    ),
                    width={"size": 4},
                ),
            ]
        ),
        html.P(),
        dbc.Row(
            dbc.Col(
                html.Div(
                    html.Button(
                        "Scan and Start Bots",
                        id="btn-scan-start",
                        n_clicks=0,
                        className="btn btn-primary",
                    ),
                    className="d-grid gap-2",
                ),
                width={"size": 6, "offset": 3},
            )
        ),
    ]
)


@callback(Output("schedule", "children"), Input("btn-start-scanning", "n_clicks"))
def btn_schedule_click(n_clicks):
    """Add scanner/screen schedule"""
    if n_clicks > 0:
        if tg_wrapper.check_schedule_running():
            return html.Button(
                "Remove Schedule",
                id="btn-schedule",
                n_clicks=0,
                name="remove",
                className="btn btn-primary",
            )
        else:
            return html.Button(
                "Add Schedule",
                id="btn-schedule",
                n_clicks=0,
                name="add",
                className="btn btn-primary",
            )


@callback(
    [Output("btn-schedule", "value"),
    Output("btn-start-scanning", "n_clicks")],
    Input("btn-schedule", "n_clicks"),
    State("btn-schedule", "name"),
)
def btn_remove_schedule_click(n_clicks, value):
    """Add scanner/screen schedule"""
    if n_clicks > 0:
        if value == "add":
            tg_wrapper._handler._check_scheduled_job()
            return "remove", 1
        if value == "remove":
            tg_wrapper._handler._remove_scheduled_job()
            return "add", 1


# @callback(
#     Output("schedule", "children"), Input("interval-container", "n_intervals")
# )
# def btn_add_schedule_update(n):
#     """ Update button with correct text """
#     if not tg_wrapper.check_schedule_running():
#         return html.Button(
#             "Add Schedule",
#             id="btn-add-schedule",
#             n_clicks=0,
#             className="btn btn-primary",
#         )
#     else:
#         return html.Button(
#             "Remove Schedule",
#             id="btn-remove-schedule",
#             n_clicks=0,
#             className="btn btn-primary",
#         )


@callback(Output("start-accordian", "start_collapsed"), Input("bots", "active_item"))
def update_output_1(value):
    """get selected value from dropdown"""
    global selected_pair
    if value is not None:
        selected_pair = value
    # update_output_2(None)
    return "true"


@callback(
    Output("bot-accordian", "start_collapsed"), Input("start-bots", "active_item")
)
def update_output_2(value):
    """get selected value from dropdown"""
    global selected_pair
    if value is not None:
        selected_pair = value
    # update_output_1(None)
    return "true"


@callback(
    Output({"type": "btn-buy", "index": MATCH}, "visible"),
    Input({"type": "btn-buy", "index": MATCH}, "n_clicks"),
)
def btn_buy_click(click):
    """Place a buy order"""
    if click > 0:
        tg_wrapper.place_market_buy_order(selected_pair)
    return html.Label()


@callback(
    Output({"type": "btn-sell", "index": MATCH}, "visible"),
    Input({"type": "btn-sell", "index": MATCH}, "n_clicks"),
)
def btn_sell_click(click):
    """Place a sell order"""
    if click > 0:
        tg_wrapper.place_market_sell_order(selected_pair)
    return html.Label()


@callback(Output("btn-open-orders", "visible"), Input("btn-open-orders", "n_clicks"))
def btn_open_orders(click):
    """restart pairs with open orders"""
    if click > 0:
        tg_wrapper.restart_open_order_pairs()
    return "true"


@callback(
    Output("market-scan-options", "children"), Input("btn-start-scanning", "n_clicks")
)
def btn_start_scanning_click(click):
    """show scan options"""
    if click > 0:
        return scan_layoutv2


@callback(
    Output("scan_options", "is_open"),
    [Input("btn-start-scanning", "n_clicks")],
    [State("scan_options", "is_open")],
)
def toggle_options_collapse(n, is_open):
    """toggle scan option collapsable"""
    if n:
        return not is_open
    return is_open


@callback(Output("btn-scan-start", "visible"), Input("btn-scan-start", "n_clicks"))
def start_scan_and_bots(n):  # pylint: disable=missing-function-docstring
    if n > 0:
        tg_wrapper.start_market_scanning()
    return "true"

@callback(Output("btn-scan-only", "visible"), Input("btn-scan-only", "n_clicks"))
def start_scan_only(n):  # pylint: disable=missing-function-docstring
    if n > 0:
        tg_wrapper.start_market_scanning(True, False)
    return "true"

@callback(Output("btn-start-only", "visible"), Input("btn-start-only", "n_clicks"))
def start_bots_only(n):  # pylint: disable=missing-function-docstring
    if n > 0:
        tg_wrapper.start_market_scanning(False, True)
    return "true"

@callback(
    Output({"type": "btn-pause", "index": MATCH}, "visible"),
    Input({"type": "btn-pause", "index": MATCH}, "n_clicks"),
)
def btn_pause_click(click):  # pylint: disable=missing-function-docstring
    # print(dash.callback_context.triggered)
    if click > 0:
        tg_wrapper.pause_bot(selected_pair)
    return "true"


@callback(
    Output({"type": "btn-resume", "index": MATCH}, "visible"),
    Input({"type": "btn-resume", "index": MATCH}, "n_clicks"),
)
def btn_resume_click(click):  # pylint: disable=missing-function-docstring
    if click > 0:
        tg_wrapper.resume_bot(selected_pair)
    return html.Label()


@callback(
    Output({"type": "btn-stop", "index": MATCH}, "visible"),
    Input({"type": "btn-stop", "index": MATCH}, "n_clicks"),
)
def btn_stop_click(click):  # pylint: disable=missing-function-docstring
    if click > 0:
        tg_wrapper.stop_bot(selected_pair)
    return html.Label()


@callback(
    Output({"type": "btn-start", "index": MATCH}, "visible"),
    Input({"type": "btn-start", "index": MATCH}, "n_clicks"),
)
def btn_start_click(click):  # pylint: disable=missing-function-docstring
    if click > 0:
        tg_wrapper.start_bot(selected_pair)
    return html.Label()


@callback(
    Output("start-accordian", "children"), Input("interval-container", "n_intervals")
)
def update_start_list(n):
    """update manual start bot list"""
    acc_list = []
    tg_wrapper.helper.read_data()
    buttons = []
    pair_count = 0
    tg_wrapper.helper.read_data()
    if "markets" in tg_wrapper.helper.data:
        markets = tg_wrapper.helper.data["markets"]
        for market in markets:
            if not tg_wrapper.helper.is_bot_running(market):
                buttons = []
                buttons.append(
                    dbc.Button(
                        "Start",
                        id={"type": "btn-start", "index": pair_count},
                        n_clicks=0,
                        className="btn btn-primary",
                    )
                )
                acc_list.append(
                    dbc.AccordionItem(
                        buttons,
                        title=f"{market} - stopped",
                        item_id=market,
                        class_name="justify-content-md-center",
                    )
                )
                pair_count += 1

    accordion = html.Div(
        dbc.Accordion(id="start-bots", children=acc_list, start_collapsed=True),
        className="d-md-block",
    )

    return accordion


@callback(
    Output("bot-accordian", "children"), Input("interval-container", "n_intervals")
)
def update_accordians(n):
    """create bot accoridans"""
    acc_list = []
    pair_count = 0
    for i in tg_wrapper.helper.get_all_bot_list():
        tg_wrapper.helper.read_data(i)
        state = "defaulted"
        if "botcontrol" in tg_wrapper.helper.data:
            state = tg_wrapper.helper.data["botcontrol"]["status"]
        buttons = []
        buttons.append(
            dbc.Button(
                "Stop",
                id={"type": "btn-stop", "index": pair_count},
                n_clicks=0,
                className="btn btn-primary",
            )
        )
        if state not in ("paused", "stopped"):
            buttons.append(
                dbc.Button(
                    "Pause",
                    id={"type": "btn-pause", "index": pair_count},
                    n_clicks=0,
                    className="btn btn-primary",
                )
            )
        if state in ("paused"):
            buttons.append(
                dbc.Button(
                    "Resume",
                    id={"type": "btn-resume", "index": pair_count},
                    n_clicks=0,
                    className="btn btn-primary",
                )
            )
        if tg_wrapper.helper.data["margin"] == " ":
            buttons.append(
                dbc.Button(
                    "Buy",
                    id={"type": "btn-buy", "index": pair_count},
                    n_clicks=0,
                    className="btn btn-primary",
                )
            )
        else:
            buttons.append(
                dbc.Button(
                    "Sell",
                    id={"type": "btn-sell", "index": pair_count},
                    n_clicks=0,
                    className="btn btn-primary",
                )
            )

        acc_list.append(
            dbc.AccordionItem(
                buttons,
                title=f"{i} - {get_bot_status(i)}",
                item_id=i,
                class_name="justify-content-md-center",
            )
        )
        pair_count += 1

    accordion = html.Div(
        dbc.Accordion(id="bots", children=acc_list, start_collapsed=True),
        className="d-md-block",
    )

    return accordion
