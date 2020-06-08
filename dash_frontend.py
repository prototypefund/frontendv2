import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import pandas as pd
from influxdb_client import InfluxDBClient
from math import isnan
from geopy.geocoders import Nominatim

def get_credentials():
    with open('credentials.txt','r') as f:
        lines = f.readlines()
        url   = lines[0].rstrip()
        token = lines[1].rstrip()
        org   = lines[2].rstrip()
    return url,token,org

def load_metadata():
    query = '''
        from(bucket: "test-hystreet")
      |> range(start: -5d) 
      |> filter(fn: (r) => r["_measurement"] == "hystreet")
      |> filter(fn: (r) => r["_field"] == "lon" or r["_field"] == "lat")
      |> unique()
      |> yield(name: "unique")
      '''
    tables = query_api.query_data_frame(query)
    geo_table = tables[["_field","_value","station_id"]].drop_duplicates()
    geo_table = geo_table.pivot(index='station_id', columns='_field', values='_value')
    geo_table = round(geo_table,5)
    
    trend=load_trend()
    tables = tables.set_index("station_id").join(trend).reset_index()
    
    geo_dict = geo_table.to_dict("index")

    info_table = tables[['station_id','ags', 'bundesland', 'city', 'landkreis', 'name','trend']]
    info_dict = info_table.set_index("station_id").drop_duplicates().to_dict("index")
    return geo_dict,info_dict

def load_trend():
    # calculate trend 
    # value of 0.2 means 20% more acitivity than 7 days ago
    query = '''
    from(bucket: "test-hystreet")
      |> range(start: -8d, stop:-7d)
      |> filter(fn: (r) => r["_measurement"] == "hystreet")
      |> filter(fn: (r) => r["_field"] == "pedestrians_count")
      |> first()
    '''
    lastweek = query_api.query_data_frame(query)
    query = '''
    from(bucket: "test-hystreet")
      |> range(start: -2d, stop:-0d)
      |> filter(fn: (r) => r["_measurement"] == "hystreet")
      |> filter(fn: (r) => r["_field"] == "pedestrians_count")
      |> last()
    '''
    current = query_api.query_data_frame(query)
    current=current[["station_id","_value"]].rename(columns={"_value":"current"}).set_index("station_id")
    lastweek=lastweek[["station_id","_value"]].rename(columns={"_value":"lastweek"}).set_index("station_id")
    df = current.join(lastweek)
    def rate(current,lastweek):
        delta = current-lastweek
        if lastweek == 0:
            return None
        else:
            return round(delta/lastweek,2)
    df["trend"] = df.apply(lambda x: rate(x["current"],x["lastweek"]), axis=1)
    #trend_dict = df[["trend"]].transpose().to_dict("records") # dict {station_id -> trend}
    return df["trend"]

def load_timeseries(station_id):
    query = '''
    from(bucket: "test-hystreet")
      |> range(start: -14d) 
      |> filter(fn: (r) => r["_measurement"] == "hystreet")
      |> filter(fn: (r) => r["_field"] == "pedestrians_count")
      |> filter(fn: (r) => r["station_id"] == "{}")
      '''.format(station_id)
    tables = query_api.query_data_frame(query)
    times  = tables["_time"]
    values = tables["_value"]
    return times, values

# global
LAT = 50
LON = 10

# set up InfluxDB query API
url,token,org = get_credentials()
client = InfluxDBClient(url=url, token=token, org=org)
query_api = client.query_api()

# Get data
geo_dict,info_dict = load_metadata()
station_ids = list(geo_dict.keys())

app = dash.Dash()

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
    elif trendvalue > 3:
        # red
        return "#cc0000"
    elif trendvalue < 0.5:
        # green
        return "#00cc22"
    else:
        # yellow
        return "#ccaa00"

#  Dash Map
map=dcc.Graph(
    id='map',
    config=config_plots,
    figure={
        'data': [dict(
            type= "scattermapbox",
            lat=[geo_dict[x]["lat"] for x in station_ids],
            lon=[geo_dict[x]["lon"] for x in station_ids],
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
        )],
        'layout': dict(
            autosize=True,
            hovermode='closest',
            height=400,
            margin = dict(l = 0, r = 0, t = 0, b = 0),
            mapbox=dict(
                style="carto-positron", # open-street-map, white-bg, carto-positron, carto-darkmatter, stamen-terrain, stamen-toner, stamen-watercolor
                bearing=0, 
                center=dict(
                    lat=LAT,
                    lon=LON
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
    dcc.Input(id="nominatim_lookup_edit", type="text", placeholder="", debounce=True),
    html.Button(id='nominatim_lookup_button', n_clicks=0, children='Suchen'),
    html.P(children=[
        "Ihr Standort: ",
        html.Span(id="nominatim_lookup_span",children=lookup_span_default),
        " ",
        html.Span(id="nominatim_lookup_span2",children=lookup_span_default),
        ]),
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
        title="Wähle einen Datenpunkt auf der map!"
        times=[]
        values=[]
    else:
        i=hoverData["points"][0]['pointIndex']
        station_id = station_ids[i]
        text = str(info_dict[station_id])
        title = "{} ({})".format(info_dict[str(station_id)]["city"],info_dict[str(station_id)]["name"])
        times, values = load_timeseries(station_id)
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

# Update map on geolocation change
@app.callback(
    Output('map', 'figure'),
    [Input('geojs_lookup_span', 'children'),
     Input('nominatim_lookup_span', 'children')],
    [State('map','figure')])
def update_map(geojs_str,nominatim_str,fig):
    ctx = dash.callback_context
    if not ctx.triggered:
        return fig
    else:
        input_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if input_id=="geojs_lookup_span":
        lat,lon = geojs_str.split(",")
        LAT=float(lat)
        LON=float(lon)
    elif input_id=="nominatim_lookup_span":
        lat,lon = nominatim_str.split(",")
        LAT=float(lat)
        LON=float(lon)
    fig["layout"]["mapbox"]["center"]["lat"]=LAT
    fig["layout"]["mapbox"]["center"]["lon"]=LON
    return fig

@app.callback(
    [Output('nominatim_lookup_span', 'children'),
     Output('nominatim_lookup_span2', 'children')],
    [Input('nominatim_lookup_button', 'n_clicks')],
    [State('nominatim_lookup_edit','value')])
def nominatim_lookup(button,query):
    geolocator = Nominatim(user_agent="everyonecounts")
    geoloc = geolocator.geocode(query,exactly_one=True)
    if geoloc:
        LAT=geoloc.latitude
        LON=geoloc.longitude
        address=geoloc.address
    else:
        address = ""
    return (str(LAT)+", "+str(LON),address)
        

# MAIN
# ==================
if __name__ == '__main__':
    print("Let's go")
    
    # start Dash webserver
    app.layout = html.Div([
        title,
        geojs_lookup_div,
        nominatim_lookup_div,
        map,
        #textbox,
        chart
    ])
    app.run_server(debug=True, host="localhost")
    