import json
import logging
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from urllib.parse import parse_qs

from utils import queries, helpers
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
BASE_URL = CONFIG["BASE_URL"]


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


map_data = get_map_data()
map_data["name"] = map_data.apply(lambda x: f'{x["name"]} ({helpers.measurementtitles[x["_measurement"]]})', 1)
dropdowndict = map_data[["name", "c_id"]].set_index("c_id").to_dict()["name"]
layout = html.Div(id="configurator", children=[
    dcc.Store(id='widgeturl', storage_type='memory'),
    html.Img(id="title",
             className="container",
             src="../assets/logo.png",
             alt="EveryoneCounts - Das Social Distancing Dashboard"),
    html.H1("Widget Konfigurator"),
    dcc.Dropdown(
        id="station",
        options=[{"label": dropdowndict[x], "value": x} for x in dropdowndict.keys()],
        value=list(dropdowndict.keys())[0]
    ),
    html.Span("Breite des Widgets (Pixel):"),
    dcc.Input(id='width', type='number', min=120, step=1),
    html.Span(" (leer lassen falls keine Breite festgelegt werden soll)"),
    dcc.Tabs(id="tabs", value='tab-timeline', children=[
        dcc.Tab(label='Zeitverlauf (Graph)',
                value='tab-timeline',
                children=[
                    html.P("Zeigt den zeitlichen Verlauf der Messpunkte an einer Station."),
                    dcc.Checklist(
                        id="timeline_checklist",
                        options=[
                            {'label': 'Trendlinie', 'value': 'show_trend'},
                            {'label': 'Gleitender Durchschnitt', 'value': 'show_rolling'},
                        ],
                        value=["show_rolling"]
                    )
                ]
                ),
        dcc.Tab(label='Auslastung (Zahl)',
                value='tab-fill',
                children=[
                    dcc.Checklist(
                        id="max_checklist",
                        options=[
                            {'label': 'Maximalen Wert angeben', 'value': 'max'},
                        ],
                        value=[]
                    ),
                    html.Div(id="max_selector",
                             children=[html.Span("Maximaler Wert: "),
                                       dcc.Input(id='max', type='number', min=0, step=1),
                                       html.Span(" (leer lassen falls kein Maximalwert genutzt werden soll)"),
                                       dcc.Dropdown(
                                           id="show_number",
                                           options=[
                                               {"label": "Zahlenwert", "value": "total"},
                                               {"label": "Prozentangabe", "value": "percentage"},
                                               {"label": "Prozentangabe & Zahlenwert", "value": "both"},
                                           ],
                                           value="both")
                                       ]),
                ])
    ]),
    dcc.Textarea(
        id='textarea',
        value='',
        style={'height': 200, 'width': '75%'},
        readOnly=True,
    ),
    html.Iframe(
        id="preview",
        src="",
        width="100%",
        height=350
    )
])


@app.callback(
    Output('widgeturl', 'value'),
    [Input('tabs', 'value'),
     Input('station', 'value'),
     Input('width', 'value'),
     Input('timeline_checklist', 'value'),
     Input('max', 'value'),
     Input('show_number', 'value'),
     Input('max_checklist', 'value')]
)
def make_widget_url(tabs, station, width, timeline_checklist, max_value, show_number, max_checklist):
    widgettype = tabs.replace("tab-", "")
    widgeturl = f"{BASE_URL}/widget?widgettype={widgettype}&station={station}"
    if width is not None:
        widgeturl += f"&width={width}"
    if widgettype == "timeline":
        show_trend = "show_trend" in timeline_checklist
        show_rolling = "show_rolling" in timeline_checklist
        widgeturl += f"&show_trend={int(show_trend)}"
        widgeturl += f"&show_rolling={int(show_rolling)}"
    elif widgettype == "fill":
        if "max" in max_checklist and max_value is not None:
            widgeturl += f"&max={int(max_value)}"
            widgeturl += f"&show_number={show_number}"
    return widgeturl


@app.callback(
    Output('max_selector', 'style'),
    [Input('max_checklist', 'value')])
def show_hide_max_selector(max_checklist):
    if "max" in max_checklist:
        return {"display": "block"}
    else:
        return {"display": "none"}


@app.callback(
    Output('textarea', 'value'),
    [Input('widgeturl', 'value')])
def update_embed_code(url):
    # TODO: show proper iframe embed code
    return url


@app.callback(
    Output('preview', 'src'),
    [Input('widgeturl', 'value')])
def update_preview(url):
    return url
