import json
import logging
import dash
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
map_data["ddname"] = map_data.apply(lambda x: f'{x["name"]} ({helpers.measurementtitles[x["_measurement"]]})', 1)
map_data.loc[~map_data["city"].isna(), "ddname"] = map_data[~map_data["city"].isna()].apply(
    lambda x: x["city"] + " " + x["ddname"], 1)
dropdowndict = map_data[["ddname", "c_id"]].set_index("c_id").to_dict()["ddname"]
layout = html.Div(id="configurator", children=[
    dcc.Store(id='widgeturl', storage_type='memory'),
    html.Img(id="title",
             className="container",
             src="../assets/logo.png",
             alt="EveryoneCounts - Das Social Distancing Dashboard"),
    html.H1("Widget Konfigurator"),
    html.H2("Auswahl der Messstation"),
    html.P("Wähle hier die Messstation aus, deren Daten Du als Widget nutzen möchtest. Du kannst durch die Liste "
           "scrollen oder mit der Tastatur suchen."),
    dcc.Dropdown(
        id="station",
        options=[{"label": dropdowndict[x], "value": x} for x in dropdowndict.keys()],
        value=list(dropdowndict.keys())[0]
    ),
    html.H2("Typ des Widgets und Details"),
    dcc.Tabs(id="tabs", value='tab-timeline', children=[
        dcc.Tab(label='Zeitverlauf (Graph)',
                value='tab-timeline',
                children=[
                    html.P("Zeigt den zeitlichen Verlauf der Messpunkte an einer Station."),
                    dcc.Checklist(
                        id="timeline_checklist",
                        options=[
                            {'label': f'{TRENDWINDOW}-Tage-Trend', 'value': 'show_trend'},
                            {'label': 'Gleitender Durchschnitt', 'value': 'show_rolling'},
                        ],
                        value=["show_rolling"])
                ]),
        dcc.Tab(label='Ampel',
                value='tab-trafficlight',
                children=[
                    html.P("Zeigt eine Ampel an, die je nach Auslastung grün, gelb oder rot ist.  Es müssen zwei "
                           "Schwellwerte angegeben werden. Der erste Wert definiert die Grenze zwischen grün und "
                           "gelb, der zweite Wert die Grenze zwischen gelb und rot."),
                    html.P(children=[
                        html.Span("Schwellwert 1:  "),
                        dcc.Input(id='t1', type='number', min=1, step=1, value=1000),
                        html.Span(" (Die Ampel ist grün wenn der Wert an der Messstation kleiner als dieser Wert ist)")
                    ]),
                    html.P(children=[
                        html.Span("Schwellwert 2:  "),
                        dcc.Input(id='t2', type='number', min=2, step=1, value=2000),
                        html.Span(" (Die Ampel ist rot wenn der Wert an der Messstation größer als dieser Wert ist)")
                    ]),
                ]),
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
    html.H2("Größe des Widgets (optional)"),
    html.Div(id="width-select", children=[
        html.P(children=[
            html.Span("Breite:  "),
            dcc.Input(id='width', type='number', min=120, step=1),
            html.Span(" Pixel. Leer lassen falls keine Breite festgelegt werden soll.")
        ]),
        html.P(children=[
            html.Span("Höhe:  "),
            dcc.Input(id='height', type='number', min=400, step=1, value=600),
            html.Span(" Pixel. Darf nicht leer sein.")
        ]),
    ]),
    html.H2("Vorschau des Widgets"),
    html.P("Der gestrichelte Rahmen ist nicht Teil des Widgets und zeigt lediglich die Größe des IFrames an."),
    html.Iframe(
        id="preview",
        src="",
        # height=350,
    ),
    html.H2("Code zum Einbetten"),
    html.P("Dies ist der Code den Du in deine Webseite einfügen musst damit das Widget angezeigt wird."),
    dcc.Textarea(
        id='textarea',
        value='',
        style={'height': 150, 'width': '75%'},
        readOnly=True,
    ),
    html.H2("Kontakt"),
    html.P(children=[
        "Für Fragen zur Nutzung oder bei Problemen kannst Du uns per Mail an ",
        html.A(children="kontakt@everyonecounts.de",
               href="mailto:kontakt@everyonecounts.de",
               target="_blank"),
        " oder auf Twitter unter ",
        html.A(children="@_everyonecounts",
               href="https://twitter.com/_everyonecounts/",
               target="_blank"),
        " erreichen."
    ]),
    html.P(html.A(children="Impressum", href="https://blog.everyonecounts.de/impressum/"))
])


@app.callback(
    Output('widgeturl', 'value'),
    [Input('tabs', 'value'),
     Input('station', 'value'),
     Input('width', 'value'),
     Input('timeline_checklist', 'value'),
     Input('max', 'value'),
     Input('show_number', 'value'),
     Input('max_checklist', 'value'),
     Input('t1', 'value'),
     Input('t2', 'value')]
)
def make_widget_url(tabs, station, width, timeline_checklist, max_value, show_number, max_checklist, t1, t2):
    widgettype = tabs.replace("tab-", "")
    widgeturl = f"{BASE_URL}/widget?widgettype={widgettype}&station={station}"
    if width is not None:
        width = width - 2 * 16  # subtract padding
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
    elif widgettype == "trafficlight":
        if t1 is not None and t2 is not None:
            widgeturl += f"&t1={t1}"
            widgeturl += f"&t2={t2}"
        else:
            return dash.no_update()
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
    [Input('widgeturl', 'value'),
     Input('width', 'value'),
     Input('height', 'value')])
def update_embed_code(url, width, height):
    if width is None:
        width = "100%"
    if height is None:
        height = 600
    title = "EveryoneCounts Widget"
    return f'<iframe src="{url}" width={width} height={height} title="{title}" style="border:none"></iframe>'


@app.callback(
    Output('preview', 'src'),
    [Input('widgeturl', 'value')])
def update_preview(url):
    return url


@app.callback(
    [Output('preview', 'width'),
     Output('preview', 'height')],
    [Input('width', 'value'),
     Input('height', 'value')])
def width_height_preview(width, height):
    if width is None:
        width = "100%"
    if height is None:
        height = 600
    return width, height
