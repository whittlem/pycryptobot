from dash import Dash, dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc

layout = html.Div([
    html.H4('Config Generator', style={'textAlign':'left'}),
    html.B(),
    dbc.Card(
    dbc.CardBody(
    html.Div([
        dbc.Label("Indicator Options"),
        dbc.Checklist(
            options=[
                {'label': 'Live Mode', 'value': 'Live'},
                {'label': 'Disable EMA', 'value': 'Disable EMA'},
                {'label': 'Disable MACD', 'value': 'Disable MACD'},
                {'label': 'Disable OBV', 'value': 'Disable OBV'},
                {'label': 'Disable Elderray', 'value': 'Disable Elderray'},
                {'label': 'Disable Failsafe Fibonacci Low ', 'value': 'Disable Failsafe Fibonacci Low'},
                {'label': 'Disable Bull Only', 'value': 'Disable Bull Only'},
                {'label': 'Disable Buy Near High', 'value': 'Disable Buy Near High'},
            ],
            value=[1],
            id="switches-indicators",
            switch=True,
            inline=True,
        ),
    ]),
    )),
    html.B(),

    dbc.Card(
    dbc.CardBody(
    html.Div([
        dbc.Label("Basic Selling Options"),
        dbc.Checklist(
            options=[
                {'label': 'Sell at a Loss', 'value': 'Sell at a Loss'},
                {'label': 'Disable OBV', 'value': 'Disable OBV'},
                {'label': 'Disable Elderray', 'value': 'Disable Elderray'},
                {'label': 'Disable Failsafe Fibonacci Low ', 'value': 'Disable Failsafe Fibonacci Low'},
                {'label': 'Disable Bull Only', 'value': 'Disable Bull Only'},
                {'label': 'Disable Buy Near High', 'value': 'Disable Buy Near High'},
            ],
            value=[1],
            id="switches-sell",
            switch=True,
            inline=True,
        ),
    ]),
    )),

    html.B(),
    dbc.Card(
    dbc.CardBody(
    html.Div([
        dbc.Label("Time Frame Options"),
        dbc.Checklist(
            options=[
                {'label': 'Smart-Switch Granularity', 'value': 'Smart-Switch Granularity'},
                {'label': 'Granularity 1 Min', 'value': 'Granularity 1 Min'},
                {'label': 'Granularity 5 Min', 'value': 'Granularity 5 Min'},
                {'label': 'Granularity 15 Min', 'value': 'Granularity 15 Min'},
                {'label': 'Granularity 1 HR', 'value': 'Granularity 1 HR'},
            ],
            value=[1],
            id="switches-sell",
            switch=True,
            inline=True,
        ),
    ]),
    )),

    html.B(),
    dbc.Card(
    dbc.CardBody(   
    html.Div([
        dbc.Label("Advance Selling Options"),

        dbc.Checklist(
            options=[
                {'label': 'Trailing Immeadiate Buy', 'value': 'Trailing Immeadiate Buy'},
                {'label': 'Prevent Loss', 'value': 'Prevent Loss'},
            ],
            value=[1],
            id="switches-advsell",
            switch=True,
            inline=True,
        ),
        dbc.Label("Prevent Loss Trigger"),
        html.B(),
        html.Div(
        dcc.Input(id="Prevent Loss Trigger", type="range", placeholder="", debounce=True, min=0, max=5, step=.05),
        ),
        dbc.Label("Prevent Loss Margin"),
        html.B(),
        html.Div(
        dcc.Input(id="Prevent Loss Margin", type="range", placeholder="", debounce=True, min=-5, max=0, step=.05),
        ),


    ])
    ))
])