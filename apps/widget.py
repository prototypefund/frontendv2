import json
import logging
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from urllib.parse import parse_qs

from utils import queries, timeline_chart, helpers
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

layout = html.Div(id="widget", children=[
    dcc.Location(id='url-widget', refresh=True),
    html.Div(id="widget-container"),
    html.Div(id="ec-attribution", children=[
        "Bereitgestellt von ",
        html.A(
            id="ec_link",
            children="EveryoneCounts",
            href="https://everyonecounts.de",
            target="_blank")
    ])
])


@app.callback(
    [Output('widget-container', 'children')],
    [Input('url-widget', 'search')]
)
def parse_url_params(url_search_str):
    urlparams = {}
    if url_search_str is not None:
        urlparams = parse_qs(url_search_str.replace("?", ""))
        print(urlparams)
    if "widgettype" not in urlparams:
        return ["You need to specify a widgettype. Either timeline or fill."]
    elif "station" not in urlparams:
        return ["You need to specify a station. Use the configurator."]
    widgettype = urlparams["widgettype"]
    station = urlparams["station"][0]
    map_data = get_map_data()
    if station not in map_data["c_id"].unique():
        return [f"Unknown station {station}"]
    if widgettype == ["timeline"]:
        show_trend = False  # default
        show_rolling = True  # default
        if "show_trend" in urlparams:
            show_trend = urlparams["show_trend"] == ["1"]
        if "show_rolling" in urlparams:
            show_rolling = urlparams["show_rolling"] == ["1"]
        CHART.update_figure("stations", station, map_data, False, [], show_trend, show_rolling)
        return [CHART.get_timeline_window(show_api_text=False)]
    elif widgettype == ["fill"]:
        station_data = map_data[map_data["c_id"] == station]
        measurement = station_data["_measurement"].tolist()[0]
        unit = helpers.measurementtitles[measurement]
        last_value = int(station_data["last_value"])
        last_time = station_data["last_time"].tolist()[0]
        last_time = last_time.strftime(helpers.timeformats[measurement])
        city = station_data['city'].tolist()[0]
        name = station_data['name'].tolist()[0]
        show_number = "total"  # default
        if city is not None and type(city) is str:
            name = f"{city} ({name})"
        output = [html.H1(id="widget-title", children=name)]
        if "max" in urlparams:
            max_value = int(urlparams["max"][0])
            percentage = round(100 * last_value / max_value, 0)
            if "show_number" in urlparams and urlparams["show_number"][0] in ["total", "percentage", "both"]:
                show_number = urlparams["show_number"][0]
            output.append(html.Div(id="widget-percentage",
                                   className=show_number,
                                   children=f"{round(percentage)}%"))
            output.append(html.Div(id="widget-total",
                                   className=show_number,
                                   children=f"{last_value} / {max_value}"))
        else:
            output.append(html.Div(id="widget-total", children=last_value))
        output.append(html.Div(id="widget-unit",
                               className=show_number,
                               children=f"{unit}"))
        output.append(html.Div(id="widget-time",
                               className=show_number,
                               children=last_time,
                               ))
        output.append(html.Div(id="widget_origin",
                               children=[
                                   "Datenquelle: ",
                                   html.A(
                                       children=helpers.originnames[measurement],
                                       href=station_data["origin"].tolist()[0],
                                       target="_blank")
                               ])
                      )
        return [output]
    else:
        return ["Unknown widgettype"]
