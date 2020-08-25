import json
import logging
import os
from datetime import datetime
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from app import app
from apps import widget, dash_frontend

# READ CONFIG
# ============
with open("config.json", "r") as f:
    CONFIG = json.load(f)

# SETUP LAYOUT
# ============
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='index-content')
])

# SET UP LOGGING
# =============
LOG_LEVEL = CONFIG["LOG_LEVEL"]
numeric_level = getattr(logging, LOG_LEVEL.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError(f'Invalid log level: {LOG_LEVEL}')
if not os.path.exists('../logs'):
    os.makedirs('logs')
logging.basicConfig(filename=datetime.now().strftime("logs/dash_frontend_%Y-%m-%d_%H-%M.log"),
                    filemode='a',  # or 'w'
                    level=numeric_level,
                    format='%(asctime)s | %(levelname)s\t| %(funcName)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# Make dash logger ('werkzeug') less chatty:
dash_logger = logging.getLogger('werkzeug')
dash_logger.setLevel(logging.WARNING)


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
    # start Dash webserver
    logging.info(f"config file contents:\n\t{CONFIG}")
    app.run_server(debug=CONFIG["DEBUG"], host=CONFIG["dash_host"])
    logging.info("Webserver started")
