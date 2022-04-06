from dash import html
import dash_bootstrap_components as dbc

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
                                dbc.Input(
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
                                dbc.Input(
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
                                dbc.Input(
                                    id="input",
                                    placeholder="Optional ... ",
                                    type="number",
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
