import os
import dash_bootstrap_components as dbc
from dash import dcc, html, callback, Output, Input, MATCH

layout = html.Div([
    dbc.Container(style={"height": "100%"}, children=
        [
            html.P(),
            dbc.Row(
                dbc.Col(
                    html.Div(dbc.Tabs(id="tabs"))
                )
            )
        ]
    ),
    dcc.Interval(id="interval-container", interval=30000, n_intervals=0),
])

@callback(
    Output("tabs", "children"),
    Input("interval-container", "n_intervals")
)
def read_log_file(n):
    """ read log file """
    tabs = []
    jsonfiles = sorted(os.listdir(os.path.join("logs")))
    tab_count = 0
    for jfile in jsonfiles:
        tabs.append(dbc.Tab(label=jfile, tab_id=jfile, id={"type": "tab", "index": tab_count}))
        tab_count += 1
    
    return tabs

@callback(
    [
        Output({"type": "tab", "index": 1}, "children"),
        # Output("tabs", "active_tab")
    ],
    Input("tabs", "active_tab")
)
def get_log_content(active_tab):
    """ read log files """
    print(active_tab)
    if active_tab is not None:
        content = dbc.Card(
                    dbc.CardBody(
                        html.Textarea(
                            str(get_last_n_lines(os.path.join("logs", active_tab), 100))
                                    .replace("\\r", "\n").replace("'", "").replace(",","").replace("[", "").replace("]", ""),
                                readOnly=True,
                                style={"width": "100%", "background": "black", "color": "white", "height": "100%"},
                                draggable=False,
                                rows=20,
                                title=active_tab
                                )
                            )
                        )
        return content #, None
    # return None, None

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
