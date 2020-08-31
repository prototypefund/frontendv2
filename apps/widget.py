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
    dcc.Location(id='url-widget', refresh=True),
    html.Div(id="timeline-chart-widget"),
    "Bereitgestellt von ",
    html.A(
        id="ec_link",
        children="EveryoneCounts",
        href="https://everyonecounts.de",
        target="_blank")
])


@app.callback(
    [Output('timeline-chart-widget', 'children')],
    [Input('url-widget', 'search')]
)
def parse_url_params(url_search_str):
    if url_search_str != None:
        urlparams = parse_qs(url_search_str.replace("?", ""))
        print(urlparams)
    if "widgettype" not in urlparams:
        return ["You need to specify a widgettype. Either timeline or fill."]
    elif "station" not in urlparams:
        return ["You need to specify a station. Use the configurator."]
    widgettype = urlparams["widgettype"]
    if widgettype == ["timeline"]:
        station = urlparams["station"][0]
        map_data = get_map_data()
        show_trend = False  # default
        show_rolling = True  # default
        if "show_trend" in urlparams:
            show_trend = urlparams["show_trend"] == ["1"]
        if "show_rolling" in urlparams:
            show_rolling = urlparams["show_rolling"] == ["1"]
        if station in map_data["c_id"].unique():
            CHART.update_figure("stations", station, map_data, False, [], show_trend, show_rolling)
            return [CHART.get_timeline_window(show_api_text=False)]
        else:
            return [f"Unknown station {station}"]
    elif widgettype == ["fill"]:
        pass
    else:
        return ["Unknown widgettype"]

