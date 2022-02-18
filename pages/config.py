from dash import Dash, dcc, html, Input, Output, callback

layout = html.Div([
    html.H4('Config', style={'textAlign':'left'}),
    html.B(),
    dcc.RadioItems(
    options=[
        {'label': 'Enable EMA', 'value': 'Enable EMA'},
        {'label': 'Enable MACD', 'value': 'Enable MACD'},
        {'label': 'Enable OBV', 'value': 'Enable OBV'},
        {'label': 'Enable TSL', 'value': 'Enable TSL'},
        {'label': 'Granularity 15M', 'value': 'Granularity 15M'},
    ],
    value='Enable MACD',

    )
])