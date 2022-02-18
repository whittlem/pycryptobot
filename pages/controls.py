import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback

from models.telegram import Wrapper

tg_wrapper = Wrapper()
selected_pair = None


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
        return f"Uptime: {tg_wrapper.helper.get_uptime()} - Status: {tg_wrapper.helper.data['botcontrol']['status']}"

layout = html.Div(
    [
        ### html buttons
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
        html.H5("Bot specific controls", style={"textAlign": "left"}),
        html.P(),
        dcc.Dropdown(
            id="dropdown",
            options=[
                {"label": i, "value": i}
                for i in tg_wrapper.helper.get_active_bot_list()
            ],
            placeholder="Select a market/pair",
            value=None,
        ),
        html.Div(id='info-status'),
        dbc.Collapse(
            dbc.Card(
                dbc.CardBody(
                    html.Div(
                        [
                            
                            html.H5(
                                "Controls",
                                style={"textAlign": "left"}),
                            html.Button(
                                "Pause",
                                id="btn-pause",
                                n_clicks=0,
                                className="btn btn-primary",
                            ),
                            html.Button(
                                "Resume",
                                id="btn-resume",
                                n_clicks=0,
                                className="btn btn-primary",
                            ),
                            html.Button(
                                "Stop",
                                id="btn-stop",
                                n_clicks=0,
                                className="btn btn-primary",
                            ),
                            html.P(),
                            html.Button(
                                "Buy",
                                hidden=update_buttons(selected_pair, " "),
                                id="btn-buy",
                                n_clicks=0,
                                className="btn btn-primary",
                            ),
                            html.Button(
                                "Sell",
                                hidden=update_buttons(selected_pair, ""),
                                id="btn-sell",
                                n_clicks=0,
                                className="btn btn-primary",
                            ),
                        ],
                        className="d-grid gap-2 col-6 mx-auto",
                    ),
                )
            ),
            id="control_list",
            is_open=False,
        ),
        html.Div(id="container-button-timestamp"),
        dcc.Interval(id="interval-container", interval=10000, n_intervals=0),
        html.Div(id="dummy-div-1"),
        html.Div(id="dummy-div-2"),
        html.Div(id="dummy-div-3"),
        html.Div(id="dummy-div-4"),
        html.Div(id="dummy-div-5"),
        html.Div(id="dummy-div-6"),
        html.Div(id="dummy-div-7"),
    ],
    className="d-grid gap-2 col-6 mx-auto",
)

scan_layout = html.Div(
    className="d-grid gap-2 col-6 mx-auto",
    children=[
        html.P(),
        html.H5("Options", style={"textAlign": "left"}),
        html.Button(
            "Add Schedule",
            id="btn-add-schedule",
            n_clicks=0,
            className="btn btn-primary",
        ),
        html.P(),
        html.Button(
            "Scan Only", id="btn-scan-only", n_clicks=0, className="btn btn-primary"
        ),
        html.Button(
            "Start Bots Only",
            id="btn-start-only",
            n_clicks=0,
            className="btn btn-primary",
        ),
        html.P(),
        html.Button(
            "Scan and Start Bots",
            id="btn-scan-start",
            n_clicks=0,
            className="btn btn-primary",
        ),
        html.P(),
    ],
)


@callback(Output("dummy-div-1", "hidden"), Input("dropdown", "value"))
def update_output_1(value):
    """get selected value from dropdown"""
    global selected_pair
    selected_pair = value
    return 'true'

@callback(Output("dummy-div-1", "children"), Input("btn-buy", "n_clicks"))
def btn_buy_click(click):
    """Place a buy order"""
    if click > 0:
        tg_wrapper.place_market_buy_order(selected_pair)
        return html.Label()


@callback(Output("dummy-div-2", "children"), Input("btn-sell", "n_clicks"))
def btn_sell_click(click):
    """Place a sell order"""
    if click > 0:
        tg_wrapper.place_market_sell_order(selected_pair)
        return html.Label()


@callback(Output("dummy-div-3", "children"), Input("btn-open-orders", "n_clicks"))
def btn_open_orders(click):
    """restart pairs with open orders"""
    if click > 0:
        tg_wrapper.restart_open_order_pairs()
        return html.Label()


@callback(
    Output("market-scan-options", "children"), Input("btn-start-scanning", "n_clicks")
)
def btn_start_scanning_click(click):
    """show scan options"""
    if click > 0:
        return scan_layout


@callback(
    Output("scan_options", "is_open"),
    [Input("btn-start-scanning", "n_clicks")],
    [State("scan_options", "is_open")],
)
def toggle_options_collapse(n, is_open):
    """toggle scon option collapsable"""
    if n:
        return not is_open
    return is_open

@callback(
    Output("dummy-div-4", "children"), Input("btn-scan-start", "n_clicks")
)
def start_scan_and_bots(n):  # pylint: disable=missing-function-docstring
    if n > 0:
        tg_wrapper.start_market_scanning()
    return html.Label()

@callback(
    Output("control_list", "is_open"),
    [Input("dropdown", "value")],
    [State("control_list", "is_open")],
)
def toggle_contol_collapse(value, is_open):
    """toggle scan option collapsable"""
    if value:
        return not is_open
    if not value and is_open:
        return not is_open
    return is_open

@callback(
    Output("info-status", "children"),
    [Input("dropdown", "value"), Input("interval-container", "n_intervals")],
)
def update_alert(value, n):
    """toggle scan option collapsable"""
    if value:
        return dbc.Alert(get_bot_status(value), color="info")
    elif selected_pair:
        return dbc.Alert(get_bot_status(selected_pair), color="info")
    return 

@callback(Output("dummy-div-5", "children"), Input("btn-pause", "n_clicks"))
def btn_pause_click(click):  # pylint: disable=missing-function-docstring
    if click > 0:
        tg_wrapper.pause_bot(selected_pair)
        return html.Label()
    return


@callback(Output("dummy-div-6", "children"), Input("btn-resume", "n_clicks"))
def btn_resume_click(click):  # pylint: disable=missing-function-docstring
    if click > 0:
        tg_wrapper.resume_bot(selected_pair)
        return html.Label()


@callback(Output("dummy-div-7", "children"), Input("btn-stop", "n_clicks"))
def btn_stop_click(click):  # pylint: disable=missing-function-docstring
    if click > 0:
        tg_wrapper.stop_bot(selected_pair)
        return html.Label()


@callback(Output("dropdown", "options"), Input("interval-container", "n_intervals"))
def update_dropdownlist(n):  # pylint: disable=missing-function-docstring
    """Update dropdown list"""
    return [{"label": i, "value": i} for i in tg_wrapper.helper.get_active_bot_list()]

# @callback(Output("info-status", "children"), Input("interval-container", "n_intervals"))
# def update_info_alert(n):  # pylint: disable=missing-function-docstring
#     """Update info bar list"""
#     return dbc.Alert(get_bot_status(selected_pair), color="info")

@callback(
    Output("btn-sell", "hidden"),
    Input("dropdown", "value"),
    Input("interval-container", "n_intervals"),
)
def update_sell_check(value, n):  # pylint: disable=missing-function-docstring
    if value is not None:
        return update_buttons(value, " ")


@callback(
    Output("btn-buy", "hidden"),
    Input("dropdown", "value"),
    Input("interval-container", "n_intervals"),
)
def update_buy_check(value, n):  # pylint: disable=missing-function-docstring
    if value is not None:
        return update_buttons(value, "")
