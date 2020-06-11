import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import pandas as pd
import geopandas as gpd

from geopy.geocoders import Nominatim
from math import isnan

from utils import queries
from utils.filter_by_radius import filter_by_radius

default_lat = 50
default_lon = 10

# Get data
query_api= queries.get_query_api()
geo_table,info_dict = queries.load_metadata(query_api)
station_ids = list(geo_table.index)

app = dash.Dash()

# hidden div for lat, lon storage
hidden_latlon = html.Div(id="hidden_latlon",style={"display":"none"})

# Title
title=html.H1(
    children='EveryoneCounts',
    style={
        'textAlign': 'center',
        'color': "#333",
        'fontFamily':'Arial, Helvetica, sans-serif'
    }
)

config_plots = dict(
    locale="de-DE",
    modeBarButtonsToRemove=['lasso2d','toggleSpikelines','toggleHover']
    )

def trend2color(trendvalue):
    if isnan(trendvalue):
        return "#999999"
    elif trendvalue > 300:
        # red
        return "#cc0000"
    elif trendvalue < 50:
        # green
        return "#00cc22"
    else:
        # yellow
        return "#ccaa00"

#  Dash Map
mainmap=dcc.Graph(
    id='map',
    config=config_plots,
    figure={
        'data': [
            dict(
                type= "scattermapbox",
                lat=list(geo_table["lat"]),
                lon=list(geo_table["lon"]),
                #lat = [40, 50, 60],
                #lon = [10, 20, 30],
                mode='markers',
                marker=dict(
                    size=12, 
                    color=[trend2color(info_dict[x]["trend"]) for x in station_ids]
                    ),
                #text=[info_dict[x]["city"]+" ("+info_dict[x]["name"]+")" for x in station_ids],
                text = ["<br>".join([key+": "+str(info_dict[station_id][key]) for key in info_dict[station_id].keys()]) for station_id in station_ids],
                hoverinfo="text",
                ),
            dict(
                type= "scattermapbox",
                lat=[50,52],
                lon=[10,9],
                mode='lines',
                )
        ],
        'layout': dict(
            autosize=True,
            hovermode='closest',
            height=400,
            margin = dict(l = 0, r = 0, t = 0, b = 0),
            mapbox=dict(
                style="carto-positron", # open-street-map, white-bg, carto-positron, carto-darkmatter, stamen-terrain, stamen-toner, stamen-watercolor
                bearing=0, 
                center=dict(
                    lat=default_lat,
                    lon=default_lon
                    ),
                pitch=0,
                zoom=6,
                )
            )
    }
)
# LINE CHART
chartlayout = dict(
            autosize=True,
            height=350,
            width=600,
            title="Wähle einen Messpunkt auf der map",
            yaxis=dict(
                title="Passanten"
                )
            )

chart = dcc.Graph(
    id='chart',
    config=config_plots,
    className="timeline-chart",
    figure={
        'data': [{
            "x" : [],
            "y" : [],
            "mode":'lines',
            }],
        'layout': chartlayout
    })

# GEOIP BOX
lookup_span_default = "?"
geojs_lookup_div = html.Div(className="lookup",children=[
    html.P('''
    Sie können Ihren Standort automatisch bestimmen lassen. Klicken Sie dazu "Meinen Standort bestimmen" und erlauben Sie Ihrem Browser auf Ihren Standort zuzugreifen.
    '''),
    html.Button(id='geojs_lookup_button', n_clicks=0, children='Meinen Standort bestimmen'),
    html.P(children=["Ihr Standort: ",html.Span(id="geojs_lookup_span",children=lookup_span_default)]),
    ])
    
# LOOKUP BOX
nominatim_lookup_div = html.Div(className="lookup",children=[
    html.P('''
    Einen Ort suchen:
    '''),
    dcc.Input(id="nominatim_lookup_edit", type="text", placeholder="", debounce=False),
    html.Button(id='nominatim_lookup_button', n_clicks=0, children='Suchen'),
    html.P(children=[
        "Ihr Standort: ",
        html.Span(id="nominatim_lookup_span",children=lookup_span_default),
        " ",
        html.Span(id="nominatim_lookup_span2",children=lookup_span_default),
        ]),
    ])

# AREA DIV
SLIDER_MAX = 120
area_div = html.Div(className="area",id="area",children=[
    html.P('''
    Wählen Sie einen Radius:
    '''),
    dcc.Slider(
        id='radiusslider',
        min=5,
        max=SLIDER_MAX,
        step=5,
        value=60,
        tooltip=dict(
            always_visible = False,
            placement = "top"
        ),
        marks = {20*x:str(20*x)+'km' for x in range(SLIDER_MAX//20+1)}
    ),
    html.Pre(id="area_output",children="")
    ])

# TEXTBOX
# textbox = html.Div(children=[
    # html.Div([
        # dcc.Markdown("""
            # **Datenauswahl**
            
            # Mouse over values in the map.
        # """),
        # html.Pre(id='textboxid')
    # ])
# ])




# CALLBACK FUNCTIONS
# ==================

# Hover over map > update timeline chart
@app.callback(
    Output('chart', 'figure'),
    [Input('map', 'hoverData')])
def display_hover_data(hoverData):
    #print("Hover",hoverData,type(hoverData))
    if hoverData==None:
        text = "Hover is NONE"
        title="Wähle einen Datenpunkt auf der Karte!"
        times=[]
        values=[]
    else:
        i=hoverData["points"][0]['pointIndex']
        station_id = station_ids[i]
        text = str(info_dict[station_id])
        title = "{} ({})".format(info_dict[str(station_id)]["city"],info_dict[str(station_id)]["name"])
        times, values = load_timeseries(query_api,station_id)
        #times=[0,1,2]
        #values=[0,5,6]
    figure={
        'data': [{
            "x" : times,
            "y" : values,
            "mode":'lines',
            }],
        'layout': chartlayout
    }
    figure["layout"]["title"]=title
    return figure

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
      return lat+", "+lon;
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
    Output(component_id='geojs_lookup_span', component_property='children'),
    [Input(component_id='geojs_lookup_button', component_property='n_clicks')]
)


# Update hidden latlon div
@app.callback(
    Output('hidden_latlon','children'),
    [Input('geojs_lookup_span', 'children'),
     Input('nominatim_lookup_span', 'children')])
def update_hidden_latlon(geojs_str,nominatim_str):
    ctx = dash.callback_context
    if not ctx.triggered:
        return ""
    else:
        input_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if input_id=="geojs_lookup_span":
        return geojs_str
    elif input_id=="nominatim_lookup_span":
        return nominatim_str
# Update map on geolocation change
@app.callback(
    [Output('map', 'figure'),
    Output('area_output','children')],
    [Input('hidden_latlon', 'children'),
     Input('radiusslider', 'value')],
    [State('map','figure')])
def update_map(hidden_latlon_str,radius,fig):
    if hidden_latlon!="":
        lat,lon = hidden_latlon_str.split(",")
        lat = float(lat)
        lon = float(lon)
    else:
        lat = default_lat
        lon = default_lon
    fig["layout"]["mapbox"]["center"]["lat"]=lat
    fig["layout"]["mapbox"]["center"]["lon"]=lon
    
    gdf = gpd.GeoDataFrame(geo_table, geometry=gpd.points_from_xy(geo_table.lon, geo_table.lat))
    gdf,poly=filter_by_radius(gdf,lat,lon,radius)
    
    x,y=poly.exterior.coords.xy
    fig["data"][1]["lat"]=y
    fig["data"][1]["lon"]=x
    return fig,str(gdf)

@app.callback(
    [Output('nominatim_lookup_span', 'children'),
     Output('nominatim_lookup_span2', 'children')],
    [Input('nominatim_lookup_button', 'n_clicks'),
     Input('nominatim_lookup_edit', 'n_submit')],
    [State('nominatim_lookup_edit','value')])
def nominatim_lookup(button,submit,query):
    geolocator = Nominatim(user_agent="everyonecounts")
    geoloc = geolocator.geocode(query,exactly_one=True)
    if geoloc:
        lat=geoloc.latitude
        lon=geoloc.longitude
        address=geoloc.address
    else:
        address = ""
    return (str(lat)+", "+str(lon),address)
        

# MAIN
# ==================
if __name__ == '__main__':
    print("Let's go")
    
    # start Dash webserver
    app.layout = html.Div([
        hidden_latlon,
        title,
        geojs_lookup_div,
        nominatim_lookup_div,
        area_div,
        mainmap,
        #textbox,
        chart
    ])
    app.run_server(debug=True, host="localhost")
    