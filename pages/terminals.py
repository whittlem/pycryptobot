import os
import dash_bootstrap_components as dbc
from dash import dcc, html, callback, Output, Input

layout = html.Div([
    dbc.Container(style={"height": "100%"}, children=
        [
            html.P(),
            dbc.Row(
                dbc.Col(
                    dcc.Dropdown(
                        id="log-dropdown",
                        options=["Item One", "Item Two"],
                        style={"color": "black"},
                    )
                )
            ),
            # dbc.Row(
            #     dbc.Col(
            #         html.Div(dbc.Tabs(id="tabs"), hidden=True)
            #     )
            # ),
            dbc.Row(
                dbc.Col(
                    html.Div(id="tab-content", style={'overflow': 'auto',
            'display': 'flex',
            'flex-direction': 'column-reverse'},)
                )
            )
        ]
    ),
    dcc.Interval(id="interval-container", interval=30000, n_intervals=0),
])

@callback(
    Output("tab-content", "children"),
    [
        Input("interval-container", "n_intervals"),
        Input("log-dropdown", "value")
    ]
)
def read_log_file(n, active_tab):
    """ read log file updated """
    content = html.Div()
    if active_tab is not None:
        log_entries = str(get_last_n_lines(active_tab, 1000))\
            .replace("', '", "\n").replace("['", "").replace("']", "").replace("\\r", "")
        # .replace("\\r", "\n").replace("'", "").replace(",","").replace("[", "").replace("]", "")

        content = dbc.Card(
                    dbc.CardBody(
                        dcc.Textarea(value=log_entries, readOnly=True,
                            style={"width": "100%", "background": "black", "color": "white", "height": "100%"},
                            draggable=False,
                            rows=20)))
    return content

# @callback(
#     Output("tab-content", "children"),
#     [
#         Input("interval-container", "n_intervals"),
#         Input("log-dropdown", "value")
#     ]
# )
# def read_logs(n, dd_value):
#     """ read log file """
# 
# #     tabs = []
# #     jsonfiles = sorted(os.listdir(os.path.join("telegram_logs")))
# #     for jfile in jsonfiles:
# #         tabs.append(dbc.Tab(label=jfile, tab_id={"path": "telegram_logs", "file": jfile}))
# # 
# #     jsonfiles = sorted(os.listdir(os.path.join("logs")))
# #     for jfile in jsonfiles:
# #         if jfile.__contains__(".log"):
# #             tabs.append(dbc.Tab(label=jfile, tab_id={"path": "logs", "file": jfile}))
#     # return tabs, active_tab, read_log_file(active_tab) if active_tab is not None else read_log_file(dd_value)
#     if dd_value is not None:
#         return read_log_file(dd_value)
#     


@callback(
    Output("log-dropdown", "options"),
    Input("interval-container", "n_intervals"),
)
def get_log_content(n):
    """ read log files add names to dropdown"""
    logs = []
    jsonfiles = sorted(os.listdir(os.path.join("telegram_logs")))
    for jfile in jsonfiles:
        logs.append({"label": jfile, "value": os.path.join("telegram_logs", jfile)})

    jsonfiles = sorted(os.listdir(os.path.join("logs")))
    for jfile in jsonfiles:
        if jfile.__contains__(".log"):
            logs.append({"label": jfile, "value": os.path.join("logs", jfile)})

    return logs

def get_last_n_lines(file_name, N):
    """ Get lines in file """
    # Create an empty list to keep the track of last N lines
    list_of_lines = []
    # Open file for reading in binary mode
    with open(file_name, 'rb') as read_obj:
        # Move the cursor to the end of the file
        read_obj.seek(0, os.SEEK_END)
        # Create a buffer to keep the last read line
        buffer = bytearray()
        # Get the current position of pointer i.e eof
        pointer_location = read_obj.tell()
        # Loop till pointer reaches the top of the file
        while pointer_location >= 0:
            # Move the file pointer to the location pointed by pointer_location
            read_obj.seek(pointer_location)
            # Shift pointer location by -1
            pointer_location = pointer_location -1
            # read that byte / character
            new_byte = read_obj.read(1)
            # If the read byte is new line character then it means one line is read
            if new_byte == b'\n':
                # Save the line in list of lines
                list_of_lines.append(buffer.decode()[::-1])
                # If the size of list reaches N, then return the reversed list
                if len(list_of_lines) == N:
                    return list(reversed(list_of_lines))
                # Reinitialize the byte array to save next line
                buffer = bytearray()
            else:
                # If last read character is not eol then add it in buffer
                buffer.extend(new_byte)

        # As file is read completely, if there is still data in buffer, then its first line.
        if len(buffer) > 0:
            list_of_lines.append(buffer.decode()[::-1])

    # return the reversed list
    return list(reversed(list_of_lines))
