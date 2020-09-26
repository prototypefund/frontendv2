import json
import logging
import os
from datetime import datetime
from time import sleep
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from app import app
from apps import widget, dash_frontend, widgetconfigurator
from utils.cached_functions import get_map_data, get_map_traces

# READ CONFIG
# ============
with open("config.json", "r") as f:
    CONFIG = json.load(f)
AUTO_REFRESH_SLOW_CACHE_ENABLE = CONFIG["AUTO_REFRESH_SLOW_CACHE_ENABLE"]
AUTO_REFRESH_SLOW_CACHE_TIME_S = CONFIG["SLOW_CACHE_CONFIG"]["CACHE_DEFAULT_TIMEOUT"]

# SETUP LAYOUT
# ============
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Interval(id='periodic-callback',
                 disabled=not AUTO_REFRESH_SLOW_CACHE_ENABLE,
                 interval=AUTO_REFRESH_SLOW_CACHE_TIME_S*1000),  # milliseconds
    html.Div(id='periodic-callback-dummy', style={"display": "none"}),
    html.Div(id='index-content'),
])

# SET UP LOGGING
# =============
LOG_LEVEL = CONFIG["LOG_LEVEL"]
print(f"LOG_LEVEL: {LOG_LEVEL}")
numeric_level = getattr(logging, LOG_LEVEL.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError(f'Invalid log level: {LOG_LEVEL}')
if not os.path.exists('logs'):
    os.makedirs('logs')
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
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
    if pathname == '/widget/configurator':
        return widgetconfigurator.layout
    else:
        return dash_frontend.layout


# AUTO-REFRESH SLOW CACHE FUNCTIONS
# =================================
@app.callback(Output('periodic-callback-dummy', 'children'),
              [Input('periodic-callback', 'n_intervals')])
def auto_refresh_cached(n_intervals):
    """
    The interval component fires a callback that makes these calls to the
    functions in the SLOW_CACHE. The result is that these expensive functions
    are called periodically without user interaction. The sleep() delay ensures
    that the functions are called a little bit after the cache expires. Thus, the
    slow cache should always be populated and no user should ever need to have to
    wait for the expensive functions to run.
    Dash does not allow callbacks without an Output, that is why a dummy element
    is required.
    """
    # sleep(10)
    # logging.debug("Auto-refreshing slow cache...")
    # get_map_data()
    # get_map_traces()
    # logging.debug(f"Auto-refresh {n_intervals} finished.")
    return n_intervals


# MAIN
# ==================
if __name__ == '__main__':
    # start Dash webserver
    logging.info(f"config file contents:\n\t{CONFIG}")
    app.run_server(debug=CONFIG["DEBUG"], host=CONFIG["dash_host"], threaded=False)
    logging.info("Webserver started")
