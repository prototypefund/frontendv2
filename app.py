import dash
import json
from flask_caching import Cache

app = dash.Dash(__name__, suppress_callback_exceptions=True)

with open("config.json", "r") as f:
    CONFIG = json.load(f)
CLEAR_CACHE_ON_STARTUP = CONFIG["CLEAR_CACHE_ON_STARTUP"]
SLOW_CACHE_CONFIG = CONFIG["SLOW_CACHE_CONFIG"]
FAST_CACHE_CONFIG = CONFIG["FAST_CACHE_CONFIG"]

slow_cache = Cache(app.server, config=SLOW_CACHE_CONFIG)
fast_cache = Cache(app.server, config=FAST_CACHE_CONFIG)
if CLEAR_CACHE_ON_STARTUP:
    slow_cache.clear()
    fast_cache.clear()
