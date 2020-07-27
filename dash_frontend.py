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
from utils import dash_elements
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
map_data["landkreis_label"] = map_data.apply(lambda x: x["landkreis"] + " " + str(x["districtType"]), 1)
CHART = timeline_chart.TimelineChartWindow(TRENDWINDOW, load_timeseries)

# SET UP DASH LAYOUT
# ======================
app.layout = html.Div(id="dash-layout", children=[
    dcc.Location(id='url', refresh=False),
    *dash_elements.storage(),
    dash_elements.mainmap(),
    dash_elements.main_controls(map_data, TRENDWINDOW),
    dash_elements.timeline_chart()
])

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
        if CHART.update_figure(detail_radio, clickData, map_data, avg):
            return [CHART.get_timeline_window()]
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
     Input('region_tabs', 'value'),
     Input('trace_visibility_checklist', 'value')],
    [State('nominatim_lookup_edit', 'value')])
def update_highlight(latlon_local_storage, radius, bundesland, landkreis, region_tabs,
                     trace_visibilty, nominatim_lookup_edit):
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
            ("region_tabs" in prop_ids and region_tabs == "tab-umkreis") or \
            ("trace_visibility_checklist" in prop_ids and region_tabs == "tab-umkreis"):
        if latlon_local_storage is not None:
            lat, lon, addr = latlon_local_storage
        else:
            lat, lon = default_lat, default_lon
            addr = "..."
        location_text = f"{addr} ({radius}km Umkreis)"
        location_editbox = addr
        filtered_map_data, poly = filter_by_radius(map_data, lat, lon, radius)

        # highlight circle
        highlight_x, highlight_y = poly.exterior.coords.xy

    elif "bundesland_dropdown" in prop_ids or \
            ("region_tabs" in prop_ids and region_tabs == "tab-bundesland") or \
            ("trace_visibility_checklist" in prop_ids and region_tabs == "tab-bundesland"):
        location_text = bundesland
        location_editbox = nominatim_lookup_edit
        filtered_map_data = map_data[map_data["bundesland"] == bundesland]
        ags = filtered_map_data["ags"].iloc[0][:-3]  # '08221' --> '08'
        highlight_x, highlight_y = get_outline_coords("bundesland", ags)

    elif "landkreis_dropdown" in prop_ids or \
            ("region_tabs" in prop_ids and region_tabs == "tab-landkreis") or \
            ("trace_visibility_checklist" in prop_ids and region_tabs == "tab-landkreis"):
        location_text = landkreis
        location_editbox = nominatim_lookup_edit
        filtered_map_data = map_data[map_data["landkreis_label"] == landkreis]
        ags = filtered_map_data["ags"].iloc[0]
        highlight_x, highlight_y = get_outline_coords("landkreis", ags)

    else:
        mean_trend_str = "nicht verfügbar"
        location_text = ""
        location_editbox = nominatim_lookup_edit
        highlight_polygon = (None, None)
        return mean_trend_str, location_text, location_editbox, highlight_polygon

    filtered_map_data = filtered_map_data[filtered_map_data["_measurement"].isin(trace_visibilty)]
    mean_trend = filtered_map_data["trend"].mean()
    highlight_polygon = (highlight_x, highlight_y)
    if np.isnan(mean_trend):
        mean_trend_str = "nicht verfügbar"
    else:
        mean_trend_str = str(int(round(mean_trend * 100))) + "%"
        if mean_trend >= 0.0:
            mean_trend_str = "+" + mean_trend_str  # show plus sign

    return mean_trend_str, location_text, location_editbox, highlight_polygon

@app.callback(
    [Output('region_container', 'style'),
     Output('trend_container', 'style')],
    [Input('detail_radio', 'value')])
def update_menu_item(detail_radio):
    show = {'display': 'block'}
    hide = {'display': 'none'}
    if detail_radio == "stations":
        return show, show
    else:
        return hide, hide


@app.callback(
    Output('map', 'figure'),
    [Input('highlight_polygon', 'data'),
     Input('detail_radio', 'value'),
     Input('trace_visibility_checklist', 'value')],
    [State('map', 'figure')])
def update_map(highlight_polygon, detail_radio, trace_visibilty, fig):
    """
    Redraw map based on level-of-detail selection and
    current highlight selection
    """

    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    prop_ids = helpers.dash_callback_get_prop_ids(ctx)
    if detail_radio == "stations":
        fig["data"] = [traces[detail_radio][0]]  # drop all except highlight
        for trace in traces[detail_radio][1:]:
            if trace["_measurement"] in trace_visibilty:
                fig["data"].append(trace)
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
    else:
        fig["data"] = traces[detail_radio]  # Update map
    return fig


@app.callback(
    Output('mean_trend_p', 'style'),
    [Input('mean_trend_span', 'children')])
def style_mean_trend(mean_str):
    mean_str = mean_str.replace("%", "")
    try:
        mean_value = float(mean_str) / 100
    except ValueError:
        mean_value = np.nan
    color = helpers.trend2color(mean_value)
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
