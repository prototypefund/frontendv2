import json
import logging
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output


from app import app
from apps import widget, dash_frontend


# SETUP LAYOUT
# ============
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='index-content')
])


# SETUP CALLBACK
# ==============
@app.callback(Output('index-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/widget':
        return widget.layout
    else:
        return dash_frontend.layout


# MAIN
# ==================
if __name__ == '__main__':
    with open("config.json", "r") as f:
        CONFIG = json.load(f)
    # start Dash webserver
    print("Let's go")
    app.run_server(debug=CONFIG["DEBUG"], host=CONFIG["dash_host"])
