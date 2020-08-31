import json
import logging
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from urllib.parse import parse_qs

from utils import queries, timeline_chart, dash_elements
from app import app, cache


# READ CONFIG
# ===========
with open("config.json", "r") as f:
    CONFIG = json.load(f)
DISABLE_CACHE = not CONFIG["ENABLE_CACHE"]  # set to true to disable caching
CLEAR_CACHE_ON_STARTUP = CONFIG["CLEAR_CACHE_ON_STARTUP"]  # for testing
CACHE_CONFIG = CONFIG["CACHE_CONFIG"]
TRENDWINDOW = CONFIG["TRENDWINDOW"]
MEASUREMENTS = CONFIG["measurements"]
LOG_LEVEL = CONFIG["LOG_LEVEL"]

# WRAPPERS
# ===============
# Wrappers around some module functions so they can be cached
# Note: using cache.cached instead of cache.memoize
# yields "RuntimeError: Working outside of request context."


@cache.memoize(unless=DISABLE_CACHE)
def get_query_api():
    url = CONFIG["influx_url"]
    org = CONFIG["influx_org"]
    token = CONFIG["influx_token"]
    return queries.get_query_api(url, org, token)


query_api = get_query_api()


@cache.memoize(unless=DISABLE_CACHE)
def get_map_data():
    logging.debug("CACHE MISS")
    return queries.get_map_data(
        query_api=query_api,
        measurements=MEASUREMENTS,
        trend_window=TRENDWINDOW)


@cache.memoize(unless=DISABLE_CACHE)
def load_timeseries(_id):
    logging.debug(f"CACHE MISS ({_id})")
    return queries.load_timeseries(query_api, _id)


# INITIALIZE CHART OBJECT
# ================
CHART = timeline_chart.TimelineChartWindow(TRENDWINDOW, load_timeseries)
map_data = get_map_data()

dropdowndict = map_data[["name", "c_id"]].set_index("c_id").to_dict()["name"]

layout = html.Div(children=[
    html.H1("Widget"),
    dcc.Dropdown(id="selection",
                 options=[{"value": key, "label": dropdowndict[key]} for key in dropdowndict],
                 value=list(dropdowndict.keys())[0]),
    html.Div(id="timeline-chart-widget")
])


@app.callback(
    [Output('timeline-chart-widget', 'children')],
    [Input('selection', 'value')]
)
def update_widget(selection):
    print("selection", selection)
    CHART.update_figure("stations", selection, get_map_data(), False, [])
    return [CHART.get_timeline_window()]