import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import numpy as np
import json

from geopy.geocoders import Nominatim
from urllib.parse import parse_qs

from utils import helpers
from utils import timeline_chart
from utils import dash_elements
from utils.filter_by_radius import filter_by_radius
from utils.get_outline_coords import get_outline_coords
from utils.ec_analytics import matomo_tracking
from utils.cached_functions import get_map_data, load_timeseries, get_map_traces

from app import app, slow_cache

with open("config.json", "r") as f:
    CONFIG = json.load(f)

# CONSTANTS
# =============
default_lat = 50
default_lon = 10
default_radius = 60

# UNPACK CONFIG
# =============
DISABLE_CACHE = not CONFIG["ENABLE_CACHE"]  # set to true to disable caching
TRENDWINDOW = CONFIG["TRENDWINDOW"]
MEASUREMENTS = CONFIG["measurements_dashboard"]
LOG_LEVEL = CONFIG["LOG_LEVEL"]


# INITIALIZE CHART OBJECT
# ================
CHART = timeline_chart.TimelineChartWindow(TRENDWINDOW, load_timeseries)

# UPDATE MEASUREMENTS
# ================
# In case there are measurements that have no data they
# should not be displayed in the layout in the next step
mapdata = get_map_data()
CONFIG["measurements"] = list(mapdata["_measurement"].unique())


# SET UP DASH LAYOUT
# ======================
layout = html.Div(id="dash-layout", children=[
    dcc.Location(id='url', refresh=False),
    *dash_elements.storage(),
    dash_elements.mainmap(),
    dash_elements.main_controls(get_map_data(), CONFIG),
    dash_elements.timeline_chart(),
    dash_elements.feedback_window()
])


# CALLBACK FUNCTIONS
# ==================

# Show/hide timeline chart
@app.callback(
    Output('chart-container', 'style'),
    [Input('map', 'clickData'),
     Input('chart-container', 'n_clicks'),
     Input('chart-close', 'n_clicks')])
def show_hide_timeline(clickDataMap, _clickDataChart, _n_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    prop_ids = helpers.dash_callback_get_prop_ids(ctx)
    # print(prop_ids)
    if "chart-close" in prop_ids:
        # clicked on close button
        return {'display': 'none'}
    elif "chart-container" in prop_ids or prop_ids is None:
        # interacted with chart
        return dash.no_update
    elif "map" in prop_ids:
        if clickDataMap is None:
            # clicked on empty map
            return {'display': 'none'}
        else:
            # clicked on data
            return {'display': 'block'}
    else:
        return {'display': 'none'}


@app.callback(
    Output("map", "clickData"),
    [Input("dash-layout", "n_clicks")])
def reset_map_clickdata(_n_clicks):
    return None


# Click map > update timeline chart
@app.callback(
    [Output('timeline-chart', 'children')],
    [Input('map', 'clickData'),
     Input('timeline-avg-check', 'value')],
    [State('detail_radio', 'value'),
     State('trace_visibility_checklist', 'value')])
def display_click_data(clickData, avg_checkbox, detail_radio, trace_visibility):
    # print(clickData)
    avg = len(avg_checkbox) > 0
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    prop_ids = helpers.dash_callback_get_prop_ids(ctx)
    if clickData is not None or "timeline-avg-check" in prop_ids:
        selection = ""
        if detail_radio == "stations" and clickData["points"][0]['curveNumber'] == 0:
            # exclude selection marker
            return dash.no_update
        elif detail_radio == "landkreis":
            selection = clickData["points"][0]['location']
        elif detail_radio == "stations":
            selection = clickData["points"][0]["customdata"]
        CHART.update_figure(detail_radio, selection, get_map_data(), avg, trace_visibility)
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
        lat = 0;
        lon = 0;
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
    if urlbar_str is not None:
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
     State('map', 'figure'),
     State("url", "search")]
)
def update_latlon_local_storage(urlbar_storage, clientside_callback_storage,
                                nominatim_storage,
                                _mapposition_lookup_button,
                                latlon_local_storage,
                                fig,
                                urlbar_str):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    prop_ids = helpers.dash_callback_get_prop_ids(ctx)
    if "urlbar_storage" in prop_ids and urlbar_str is not None and urlbar_str != "":
        lat = urlbar_storage[0]
        lon = urlbar_storage[1]
        addr = nominatim_reverse_lookup(lat, lon)
        return lat, lon, addr
    elif "clientside_callback_storage" in prop_ids and \
            clientside_callback_storage[0] != 0 and \
            clientside_callback_storage[1] != 0:
        lat, lon, _ = clientside_callback_storage
        if (lat, lon) == (0, 0):
            return latlon_local_storage  # original value, don't change
        else:
            addr = nominatim_reverse_lookup(lat, lon)
            return lat, lon, addr
    elif prop_ids[0] == "mapposition_lookup_button":
        lat = fig["layout"]["mapbox"]["center"]["lat"]
        lon = fig["layout"]["mapbox"]["center"]["lon"]
        addr = nominatim_reverse_lookup(lat, lon)
        return lat, lon, addr
    elif prop_ids[0] == "nominatim_storage" and nominatim_storage[2] != "":
        return nominatim_storage
    else:
        return latlon_local_storage  # original value, don't change


# Update permalink
# @app.callback(
#     Output('permalink', 'href'),
#     [Input('latlon_local_storage', 'data'),
#      Input('radiusslider', 'value')])
# def update_permalink(latlon_local_storage, radius):
#     lat, lon, _ = latlon_local_storage
#     return f"?lat={lat}&lon={lon}&radius={radius}"


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

    map_data = get_map_data()

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
        matomo_tracking("EC_Dash_Highlight_Radius")

    elif "bundesland_dropdown" in prop_ids or \
            ("region_tabs" in prop_ids and region_tabs == "tab-bundesland") or \
            ("trace_visibility_checklist" in prop_ids and region_tabs == "tab-bundesland"):
        location_text = bundesland
        location_editbox = nominatim_lookup_edit
        filtered_map_data = map_data[map_data["bundesland"] == bundesland]
        ags = filtered_map_data["ags"].iloc[0][:-3]  # '08221' --> '08'
        highlight_x, highlight_y = get_outline_coords("bundesland", ags)
        matomo_tracking("EC_Dash_Highlight_Bundesland")

    elif "landkreis_dropdown" in prop_ids or \
            ("region_tabs" in prop_ids and region_tabs == "tab-landkreis") or \
            ("trace_visibility_checklist" in prop_ids and region_tabs == "tab-landkreis"):
        location_text = landkreis
        location_editbox = nominatim_lookup_edit
        filtered_map_data = map_data[map_data["landkreis_label"] == landkreis]
        ags = filtered_map_data["ags"].iloc[0]
        highlight_x, highlight_y = get_outline_coords("landkreis", ags)
        matomo_tracking("EC_Dash_Highlight_Landkreis")

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
    [Output("btn-region-select", "children"),
     Output("region_container", "style")],
    [Input("btn-region-select", "n_clicks")],
    [State('detail_radio', 'value')])
def show_hide_region_select(n_clicks, detail_radio):
    if n_clicks is None:
        return dash.no_update, dash.no_update
    if n_clicks % 2 == 1 and detail_radio == "stations":
        # show
        matomo_tracking("EC_Dash_Show_Region_Select")
        return "Auswahl einklappen ↑", {'display': 'block'}
    else:
        # hide
        return "Region auswählen ↓", {'display': 'none'}


@app.callback(
    [Output("btn-info", "children"),
     Output("infotext", "style")],
    [Input("btn-info", "n_clicks"),
     Input("btn-info-close", "n_clicks")])
def show_hide_info(n_clicks, n_clicks_close):
    ctx = dash.callback_context
    if (n_clicks is None and n_clicks_close is None) or not ctx.triggered:
        return dash.no_update, dash.no_update
    elif n_clicks_close is None:
        n_clicks_close = 0
    prop_ids = helpers.dash_callback_get_prop_ids(ctx)
    if "btn-info-close" in prop_ids or (n_clicks + n_clicks_close) % 2 == 0:
        # hide
        return "Informationen anzeigen ↓", {'display': 'none'}
    else:
        # show
        matomo_tracking("EC_Dash_Show_Infobox")
        return "Informationen ausblenden ↑", {'display': 'block'}


@app.callback(
    [Output("detail_container", "style"),
     Output("btn-main-toolbar", "children")],
    [Input("btn-main-toolbar", "n_clicks")])
def show_hide_tools(n_clicks):
    ctx = dash.callback_context
    if n_clicks is None or not ctx.triggered:
        return dash.no_update, dash.no_update
    if n_clicks % 2 == 0:
        # hide
        return {'display': 'none'}, f"Optionen anzeigen ↓"
    else:
        # show
        matomo_tracking("EC_Dash_Show_Infobox")
        return {'display': 'block'}, f"Optionen ausblenden ↑"


@app.callback(
    Output('trend_container', 'style'),
    [Input('detail_radio', 'value'),
     Input("btn-main-toolbar", "n_clicks")])
def update_trend_container_display(detail_radio, n_clicks):
    ctx = dash.callback_context
    prop_ids = helpers.dash_callback_get_prop_ids(ctx)
    if "btn-main-toolbar" in prop_ids:
        if n_clicks is None or not ctx.triggered:
            return dash.no_update
        if n_clicks % 2 == 0:
            return {'display': 'none'}
        else:
            return {'display': 'block'}
    if "detail_radio" in prop_ids:
        if detail_radio == "stations":
            return {'display': 'block'}
        else:
            return {'display': 'none'}


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
    traces = get_map_traces(trace_visibilty)
    fig["data"] = traces[detail_radio]  # Update map
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
def nominatim_lookup_callback(_button, _submit, query):
    return nominatim_lookup(query)


@app.callback(
    Output('feedback-container', 'style'),
    [Input('feedback-close', 'n_clicks')])
def hide_feedback_box(n_clicks):
    if n_clicks is not None:
        return {"display": "none"}
    else:
        return dash.no_update


@slow_cache.memoize(unless=DISABLE_CACHE)
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
    return lat, lon, address


@slow_cache.memoize(unless=DISABLE_CACHE)
def nominatim_reverse_lookup(lat, lon):
    # lat,lon --> location name
    geolocator = Nominatim(user_agent="everyonecounts")
    query = f"{lat}, {lon}"
    geoloc = geolocator.reverse(query, exactly_one=True)
    address = ""
    if geoloc:
        if "address" not in geoloc.raw:
            return ""
        addressparts = geoloc.raw["address"]
        addresslist = []
        for part in ['hamlet', 'village', 'city_district', 'city', 'county', 'state']:
            if part in addressparts:
                addresslist.append(addressparts[part])
        address = ", ".join(addresslist[-4:])  # dont make name too long
    return address
