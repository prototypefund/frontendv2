import dash
import json
from flask_caching import Cache

app = dash.Dash(__name__, suppress_callback_exceptions=True)

with open("config.json", "r") as f:
    CONFIG = json.load(f)
CLEAR_CACHE_ON_STARTUP = CONFIG["CLEAR_CACHE_ON_STARTUP"]
CACHE_CONFIG = CONFIG["CACHE_CONFIG"]

cache = Cache(app.server, config=CACHE_CONFIG)
if CLEAR_CACHE_ON_STARTUP:
    cache.clear()
