import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from flask_caching import Cache
import numpy as np
import pandas as pd
import geopandas as gpd
import json

from geopy.geocoders import Nominatim
from urllib.parse import parse_qs

from utils import queries
from utils import helpers
from utils import map_traces
from utils import timeline_chart
from utils.filter_by_radius import filter_by_radius
from utils.get_outline_coords import get_outline_coords

# CONSTANTS
# =============
default_lat = 50
default_lon = 10
default_radius = 60

# READ CONFIG
# ==========
with open("config.json", "r") as f:
    CONFIG = json.load(f)
DISABLE_CACHE = not CONFIG["ENABLE_CACHE"]  # set to true to disable caching
CLEAR_CACHE_ON_STARTUP = CONFIG["CLEAR_CACHE_ON_STARTUP"]  # for testing
TRENDWINDOW = CONFIG["TRENDWINDOW"]

# DASH SETUP
# =======
app = dash.Dash()
app.title = 'EveryoneCounts'
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache',
    'CACHE_THRESHOLD': 100,  # max cache size in items
    'CACHE_DEFAULT_TIMEOUT': 3600  # seconds
    # see https://pythonhosted.org/Flask-Caching/
})
if CLEAR_CACHE_ON_STARTUP:
    cache.clear()


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
    return queries.get_map_data(query_api=query_api, trend_window=TRENDWINDOW)


@cache.memoize(unless=DISABLE_CACHE)
def load_timeseries(_id):
    return queries.load_timeseries(query_api, _id)


@cache.memoize(unless=DISABLE_CACHE)
def get_map_traces(map_data):
    return map_traces.get_map_traces(map_data=map_data)


# LOAD MAP DATA
# ================
map_data = get_map_data()  # map_data is a GeoDataFrame
map_data, traces = get_map_traces(map_data)  # traces for main map
chart = timeline_chart.TimelineChartWindow(TRENDWINDOW, load_timeseries)

# SET UP DASH ELEMENTS
# ======================

# dcc Storage
storage = [
    dcc.Store(id='clientside_callback_storage', storage_type='memory'),
    dcc.Store(id='nominatim_storage', storage_type='memory'),
    dcc.Store(id='urlbar_storage', storage_type='memory'),
    dcc.Store(id='highlight_polygon', storage_type='memory'),
    dcc.Store(id='latlon_local_storage', storage_type='local'),
]
# Title
title = html.H1(
    children='EveryoneCounts',
    style={
        'textAlign': 'center',
        'color': "#333",
        'fontFamily': 'Arial, Helvetica, sans-serif'
    }
)

config_plots = dict(
    locale="de-DE",
    displaylogo=False,
    modeBarButtonsToRemove=['lasso2d',
                            'toggleSpikelines',
                            'toggleHover',
                            'select2d',
                            'autoScale2d',
                            'resetScale2d',
                            'resetViewMapbox'],
    displayModeBar=True,
    responsive=True
)

#  Dash Map
main_map_name = "Messpunkte"
mainmap = dcc.Graph(
    id='map',
    config=config_plots,
    figure={
        'data': traces["stations"],
        'layout': dict(
            autosize=True,
            hovermode='closest',
            showlegend=True,
            legend_title_text='Datenquelle',
            legend=dict(
                x=0.5,
                y=1,
                traceorder="normal",
                font=dict(
                    family="sans-serif",
                    size=14,
                    color="black"
                ),
                bgcolor="#fff",
                bgopacity=0.3,
                bordercolor="#eee",
                borderwidth=1
            ),
            # height=400,
            margin=dict(l=0, r=0, t=0, b=0),
            mapbox=dict(
                style="carto-positron",
                # open-street-map,
                # white-bg,
                # carto-positron,
                # carto-darkmatter,
                # stamen-terrain,
                # stamen-toner,
                # stamen-watercolor
                bearing=0,
                center=dict(
                    lat=default_lat,
                    lon=default_lon
                ),
                pitch=0,
                zoom=6,
            )
        ),
    },
)
# LINE CHART

chartDiv = html.Div(id="chart-container", style={'display': 'none'}, children=[
    html.Button(id="chart-close", children=" × "),
    dcc.Loading(
        id="timeline-chart",
        type="circle",
        children=[
            dcc.Checklist(id="timeline-avg-check", value=[])
            # This checklist  needs to be in the layout because
            # a callback is bound to it. Otherwise, Dash 1.12 will throw errors
            # This is an issue even when using app.validation_layout or
            # suppress_callback_exceptions=True, as suggested in the docs
            # Don't trust the documentation in this case.
        ]
    ),
])

# LOOKUP BOX
SLIDER_MAX = 120
lookup_span_default = "?"
location_lookup_div = html.Div(className="", children=[
    html.H3("Mittelpunkt bestimmen:"),
    html.Div(id="search-container", children=[
        dcc.Input(id="nominatim_lookup_edit", type="text", placeholder="", debounce=False),
        html.Button(id='nominatim_lookup_button', n_clicks=0, children='Suchen'),
    ]),
    html.Button(id='geojs_lookup_button', n_clicks=0, children='Automatisch bestimmen'),
    html.Button(id='mapposition_lookup_button', n_clicks=0, children='Kartenmittelpunkt verwenden'),
    html.H3("Umkreis:"),
    dcc.Slider(
        id='radiusslider',
        min=5,
        max=SLIDER_MAX,
        step=5,
        value=60,
        tooltip=dict(
            always_visible=False,
            placement="top"
        ),
        marks={20 * x: str(20 * x) + 'km' for x in range(SLIDER_MAX // 20 + 1)}
    )
])

map_data["landkreis_label"] = map_data.apply(lambda x: x["landkreis"] + " " + str(x["districtType"]), 1)
landkreis_options = [{'label': x, 'value': x} for x in sorted(map_data["landkreis_label"].unique())]
bundesland_options = [{'label': x, 'value': x} for x in sorted(map_data["bundesland"].unique())]
region_container = html.Div(id="region_container", className="container", children=[
    dcc.Tabs(id='region_tabs', className="", value='tab-umkreis', children=[
        dcc.Tab(label='Umkreis', value='tab-umkreis', children=[
            location_lookup_div
        ]),
        dcc.Tab(label='Landkreis', value='tab-landkreis', children=[
            html.H3("Wähle einen Landkreis:"),
            dcc.Dropdown(
                id='landkreis_dropdown',
                options=landkreis_options,
                value=landkreis_options[0]["value"],
                clearable=False
            ),
            html.P("Hinweis: Nur Landkreise mit Datenpunkten können ausgewählt werden!"),
        ]),
        dcc.Tab(label='Bundesland', value='tab-bundesland', children=[
            html.H3("Wähle ein Bundesland:"),
            dcc.Dropdown(
                id='bundesland_dropdown',
                options=bundesland_options,
                value=bundesland_options[0]["value"],
                clearable=False
            ),
        ]),
    ])
])

trend_container = html.Div(id="trend_container", className="container", children=[
    html.Div(children=[
        html.H3(f"{TRENDWINDOW}-Tage-Trend im gewählten Bereich:"),
        html.P(id="mean_trend_p", style={}, children=[
            html.Span(id="mean_trend_span", children=""),
            "%"
        ]),
    ]),
    html.Div(children=[
        html.H3("Detailgrad"),
        dcc.RadioItems(
            id="detail_radio",
            options=[
                {'label': 'Messstationen', 'value': 'stations'},
                {'label': 'Landkreise', 'value': 'landkreis'},
                {'label': 'Bundesländer', 'value': 'bundesland'}
            ],
            value='stations',
            labelStyle={'display': 'inline-block'}
        ),
    ]),

    html.P(id="location_p", children=[
        html.Span(children="Region: ", style={"fontWeight": "bold"}),
        html.Span(id="location_text", children=lookup_span_default),
        " ",
        html.A(children="(Ändern)", style={"textDecoration": "underline"}),
    ]),
    dcc.Checklist(
        options=[
            {'label': 'Fußgänger (Hystreet)', 'value': 'hystreet'},
            {'label': 'Fußgänger (Webcams)', 'value': 'webcams'},
            {'label': 'Fahrradfahrer', 'value': 'bikes'},
            {'label': 'Popularität (Google)', 'value': 'google_maps'},
            {'label': 'Luftqualität', 'value': 'airquality'}
        ],
        value=['hystreet', 'webcams', 'bikes', 'google_maps'],
        labelStyle={'display': 'block'}
    ),
    html.P(html.A(id="permalink", children="Permalink", href="xyz")),
])

layout = [
    dcc.Location(id='url', refresh=False),
    *storage,
    title,
    mainmap,
    trend_container,
    region_container,
    chartDiv
]
app.layout = html.Div(id="dash-layout", children=layout)


# CALLBACK FUNCTIONS
# ==================

# Show/hide timeline chart
@app.callback(
    Output('chart-container', 'style'),
    [Input('map', 'clickData'),
     Input('chart-container', 'n_clicks'),
     Input('chart-close', 'n_clicks')])
def show_hide_timeline(clickDataMap, clickDataChart, n_clicks):
    #print("clickData:", clickDataMap, type(clickDataMap))
    if clickDataMap is None and clickDataChart is None:
        return {'display': 'none'}
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    prop_ids = helpers.dash_callback_get_prop_ids(ctx)
    print(prop_ids)
    if "chart-close" in prop_ids:
        return {'display': 'none'}
    elif "map" in prop_ids or "chart-container" in prop_ids:
        return {'display': 'block'}
    else:
        return {'display': 'none'}


@app.callback(
    Output("map", "clickData"),
    [Input("dash-layout", "n_clicks")])
def reset_map_clickdata(n_clicks):
    return None


# Click map > update timeline chart
@app.callback(
    [Output('timeline-chart', 'children')],
    [Input('map', 'clickData'),
     Input('timeline-avg-check', 'value')],
    [State('detail_radio', 'value')])
def display_click_data(clickData, avg_checkbox, detail_radio):
    avg = len(avg_checkbox) > 0
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    prop_ids = helpers.dash_callback_get_prop_ids(ctx)
    if clickData is not None or "timeline-avg-check" in prop_ids:
        if chart.update_figure(detail_radio, clickData, map_data, avg):
            return [chart.get_timeline_window()]
    return dash.no_update


# Click Button > get JS GeoIP position
app.clientside_callback(
    """
    function(x) {
        return getLocation();
    }
    var lat = 0;
    var lon = 0;

    function getLocation() {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(showPosition);
      } else { 
        showPosition('error');
      }
      //return lat+","+lon;
      return [lat,lon,""];
    }

    function showPosition(position) {
      if (position=='error') {
        lat = -1;
        lon = -1;
      } else {
        lat = position.coords.latitude;
        lon = position.coords.longitude;
      }
    }
    """,
    Output(component_id='clientside_callback_storage', component_property='data'),
    [Input(component_id='geojs_lookup_button', component_property='n_clicks')]
)


# Read data from url parameters:
@app.callback(
    [Output("urlbar_storage", "data"),
     Output("radiusslider", "value")],
    [Input("url", "search")])
def update_from_url(urlbar_str):
    paramsdict = dict(
        lat=default_lat,
        lon=default_lon,
        radius=default_radius)
    if urlbar_str != None:
        urlparams = parse_qs(urlbar_str.replace("?", ""))
        for key in paramsdict:
            try:
                paramsdict[key] = float(urlparams[key][0])
            except:
                pass
    return (paramsdict["lat"], paramsdict["lon"]), paramsdict["radius"]


# Update current position
# either from
# - Nominatim lookup
# - GeoJS position
# - Center of map button
# - from urlbar parameters (on load)
@app.callback(
    Output('latlon_local_storage', 'data'),
    [Input('urlbar_storage', 'data'),
     Input('clientside_callback_storage', 'data'),
     Input('nominatim_storage', 'data'),
     Input('mapposition_lookup_button', 'n_clicks')],
    [State('latlon_local_storage', 'data'),
     State('map', 'figure')]
)
def update_latlon_local_storage(urlbar_storage, clientside_callback_storage,
                                nominatim_storage,
                                mapposition_lookup_button,
                                latlon_local_storage,
                                fig):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    prop_ids = helpers.dash_callback_get_prop_ids(ctx)
    if "urlbar_storage" in prop_ids:
        lat = urlbar_storage[0]
        lon = urlbar_storage[1]
        addr = nominatim_reverse_lookup(lat, lon)
        return (lat, lon, addr)
    elif prop_ids[0] == "clientside_callback_storage":
        lat, lon, _ = clientside_callback_storage
        if (lat, lon) == (0, 0):
            return latlon_local_storage  # original value, don't change
        else:
            addr = nominatim_reverse_lookup(lat, lon)
            return (lat, lon, addr)
    elif prop_ids[0] == "mapposition_lookup_button":
        lat = fig["layout"]["mapbox"]["center"]["lat"]
        lon = fig["layout"]["mapbox"]["center"]["lon"]
        addr = nominatim_reverse_lookup(lat, lon)
        return (lat, lon, addr)
    elif prop_ids[0] == "nominatim_storage" and nominatim_storage[2] != "":
        return nominatim_storage
    else:
        return latlon_local_storage  # original value, don't change


# Update permalink
@app.callback(
    Output('permalink', 'href'),
    [Input('latlon_local_storage', 'data'),
     Input('radiusslider', 'value')])
def update_permalink(latlon_local_storage, radius):
    lat, lon, _ = latlon_local_storage
    return f"?lat={lat}&lon={lon}&radius={radius}"


# Update highlight on geolocation change or BL/LK selection
@app.callback(
    [
        Output('mean_trend_span', 'children'),
        Output('location_text', 'children'),
        Output('nominatim_lookup_edit', 'value'),
        Output('highlight_polygon', 'data')],
    [Input('latlon_local_storage', 'data'),
     Input('radiusslider', 'value'),
     Input('bundesland_dropdown', 'value'),
     Input('landkreis_dropdown', 'value'),
     Input('region_tabs', 'value')],
    [State('nominatim_lookup_edit', 'value')])
def update_highlight(latlon_local_storage, radius, bundesland, landkreis, region_tabs,
                     nominatim_lookup_edit):
    """
    Based on selected region (radius+center or landkreis or bundesland) change the following:
    - Region name
    - Highlighted region on map
    - Trend value (recalculate)
    """
    ctx = dash.callback_context
    prop_ids = helpers.dash_callback_get_prop_ids(ctx)  # origin of callback

    if 'latlon_local_storage' in prop_ids or \
            'radiusslider' in prop_ids or \
            ("region_tabs" in prop_ids and region_tabs == "tab-umkreis"):
        if latlon_local_storage is not None:
            lat, lon, addr = latlon_local_storage
        else:
            lat, lon = default_lat, default_lon
            addr = "..."
        location_text = f"{addr} ({radius}km Umkreis)"
        location_editbox = addr
        filtered_map_data, poly = filter_by_radius(map_data, lat, lon, radius)
        mean_trend = filtered_map_data["trend"].mean()

        # highlight circle
        highlight_x, highlight_y = poly.exterior.coords.xy

    elif "bundesland_dropdown" in prop_ids or \
            ("region_tabs" in prop_ids and region_tabs == "tab-bundesland"):
        location_text = bundesland
        location_editbox = nominatim_lookup_edit
        filtered_map_data = map_data[map_data["bundesland"] == bundesland]
        ags = filtered_map_data["ags"].iloc[0][:-3]  # '08221' --> '08'
        mean_trend = filtered_map_data["trend"].mean()
        highlight_x, highlight_y = get_outline_coords("bundesland", ags)

    elif "landkreis_dropdown" in prop_ids or \
            ("region_tabs" in prop_ids and region_tabs == "tab-landkreis"):
        location_text = landkreis
        location_editbox = nominatim_lookup_edit
        filtered_map_data = map_data[map_data["landkreis_label"] == landkreis]
        ags = filtered_map_data["ags"].iloc[0]
        mean_trend = filtered_map_data["trend"].mean()
        highlight_x, highlight_y = get_outline_coords("landkreis", ags)

    else:
        mean_trend = ""
        location_text = ""
        location_editbox = nominatim_lookup_edit
        highlight_x, highlight_y = None, None

    highlight_polygon = (highlight_x, highlight_y)
    if np.isnan(mean_trend):
        mean_trend_str = ""
    else:
        mean_trend_str = str(int(round(mean_trend * 100)))
        if mean_trend >= 0.0:
            mean_trend_str = "+" + mean_trend_str  # show plus sign

    return mean_trend_str, location_text, location_editbox, highlight_polygon


@app.callback(
    [Output('map', 'figure'),
     Output('region_container', 'style')],
    [Input('highlight_polygon', 'data'),
     Input('detail_radio', 'value')],
    [State('map', 'figure')])
def update_map(highlight_polygon, detail_radio, fig):
    """
    Redraw map based on level-of-detail selection and
    current highlight selection
    """

    fig["data"] = traces[detail_radio]  # Update map

    # Handle highlight display
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    prop_ids = helpers.dash_callback_get_prop_ids(ctx)
    if detail_radio == "stations":
        highlight_x, highlight_y = highlight_polygon
        # draw highligth into trace0
        fig["data"][0]["lat"] = highlight_y
        fig["data"][0]["lon"] = highlight_x
        if "highlight_polygon" in prop_ids:
            # center and zoom map
            zoom, centerlat, centerlon = helpers.calc_zoom(highlight_y, highlight_x)
            fig["layout"]["mapbox"]["center"]["lat"] = centerlat
            fig["layout"]["mapbox"]["center"]["lon"] = centerlon
            fig["layout"]["mapbox"]["zoom"] = zoom
        region_container_style = {'display': 'block'}
    else:
        region_container_style = {'display': 'none'}
    return fig, region_container_style


@app.callback(
    Output('mean_trend_p', 'style'),
    [Input('mean_trend_span', 'children')])
def style_mean_trend(mean_str):
    color = helpers.trend2color(float(mean_str) / 100)
    return dict(background=color)


@app.callback(
    Output('nominatim_storage', 'data'),
    [Input('nominatim_lookup_button', 'n_clicks'),
     Input('nominatim_lookup_edit', 'n_submit')],
    [State('nominatim_lookup_edit', 'value')])
def nominatim_lookup_callback(button, submit, query):
    return nominatim_lookup(query)


@cache.memoize(unless=DISABLE_CACHE)
def nominatim_lookup(query):
    # Location name --> lat,lon
    geolocator = Nominatim(user_agent="everyonecounts")
    geoloc = geolocator.geocode(query, exactly_one=True)
    if geoloc:
        lat = geoloc.latitude
        lon = geoloc.longitude
        address = geoloc.address
        address = address.replace(", Deutschland", "")
    else:
        address = ""
        lat = default_lat
        lon = default_lon
    return (lat, lon, address)


@cache.memoize(unless=DISABLE_CACHE)
def nominatim_reverse_lookup(lat, lon):
    # lat,lon --> location name
    geolocator = Nominatim(user_agent="everyonecounts")
    query = f"{lat}, {lon}"
    geoloc = geolocator.reverse(query, exactly_one=True)
    address = ""
    if geoloc:
        addressparts = geoloc.raw["address"]
        addresslist = []
        for part in ['hamlet', 'village', 'city_district', 'city', 'county', 'state']:
            if part in addressparts:
                addresslist.append(addressparts[part])
        address = ", ".join(addresslist[-4:])  # dont make name too long
    return address


# MAIN
# ==================
if __name__ == '__main__':
    # start Dash webserver
    print("Let's go")
    app.run_server(debug=CONFIG["DEBUG"], host=CONFIG["dash_host"], threaded=False)
