from dash import html
import dash_bootstrap_components as dbc
from models.telegram import Wrapper
# from models.exchange import Granularity

tg_wrapper = Wrapper("config.json", "webgui")
tg_wrapper.helper.read_config()

tg_token = tg_wrapper.helper.config["telegram"]["token"]
tg_userid = tg_wrapper.helper.config["telegram"]["user_id"]
tg_clientid = tg_wrapper.helper.config["telegram"]["client_id"]

layout = html.Div(
    [
        html.H4("Telegram Config", style={"textAlign": "left"}),
        html.B(),
        html.H5("Options"),
        html.Div(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                dbc.Label("Telegram Token"),
                                dbc.Input(value=tg_token,
                                    id="input",
                                    placeholder="Enter Token ... ",
                                    type="password",
                                ),
                                dbc.FormText(
                                    "Token Format: nnnnnnnnnn:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                                ),
                            ]
                        ),
                        html.Br(),
                        html.Div(
                            [
                                dbc.Label("Telegram User Id"),
                                dbc.Input(value=tg_userid,
                                    id="input",
                                    placeholder="Enter Id ... ",
                                    type="password",
                                ),
                                dbc.FormText("User Id format: nnnnnnnnnn"),
                            ]
                        ),
                        html.Br(),
                        html.Div(
                            [
                                dbc.Label("Telegram Group Id"),
                                dbc.Input(value=tg_clientid,
                                    id="input",
                                    placeholder="Optional ... ",
                                    type="password",
                                ),
                                dbc.FormText(
                                    "Group Id format: nnnnnnnnnnnn  (it might include - at the start)"
                                ),
                            ]
                        ),
                    ]
                )
            )
        ),
    ]
)
