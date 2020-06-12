import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from flask_caching import Cache
import pandas as pd
import geopandas as gpd

from geopy.geocoders import Nominatim

from utils import queries
from utils import helpers
from utils.filter_by_radius import filter_by_radius

default_lat = 50
default_lon = 10

# Get data
query_api= queries.get_query_api()
metadata = queries.load_metadata(query_api) # metadata is a GeoDataFrame

app = dash.Dash()
app.title = 'EveryoneCounts'
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache',
    'CACHE_THRESHOLD': 100, # max cache size in items
    'CACHE_DEFAULT_TIMEOUT': 3600 # seconds
    # see https://pythonhosted.org/Flask-Caching/
    })
DISABLE_CACHE = False # set to true to disable caching
    
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

#  Dash Map
main_map_name = "Messpunkte"
mainmap=dcc.Graph(
    id='map',
    config=config_plots,
    figure={
        'data': [
            dict(
                # TRACE 0: radius selection marker
                name="Filter radius",
                type= "scattermapbox",
                fill = "toself",
                fillcolor = 'rgba(135, 206, 250, 0.3)',
                marker=dict(
                    color='rgba(135, 206, 250, 0.0)',
                    ),
                hoverinfo='skip',
                lat=[],
                lon=[],
                mode='lines',
                ),
            dict(
                # TRACE 1: Datapoints
                name=main_map_name,
                type= "scattermapbox",
                lat=metadata["lat"],
                lon=metadata["lon"],
                #lat = [40, 50, 60],
                #lon = [10, 20, 30],
                mode='markers',
                marker=dict(
                    size=20, 
                    color=metadata.apply(lambda x: helpers.trend2color(x["trend"]),axis=1)
                    ),
                #text = ["<br>".join([key+": "+str(info_dict[station_id][key]) for key in info_dict[station_id].keys()]) for station_id in station_ids],
                text = helpers.tooltiptext(metadata),
                hoverinfo="text",
                ),
        ],
        'layout': dict(
            autosize=True,
            hovermode='closest',
            showlegend=False,
            #height=400,
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
selectorOptions = dict(
    buttons = [
        {
            "step": 'all',
            "label": 'Gesamt'
        },{
            "step": 'year',
            "stepmode": 'backward',
            "count": 1,
            "label": 'Jahr'
        },{
            "step": 'month',
            "stepmode": 'backward',
            "count": 3,
            "label": '3 Monate'
        },{
            "step": 'month',
            "stepmode": 'backward',
            "count": 1,
            "label": 'Monat'
        },{
            "step": 'day',
            "stepmode": 'backward',
            "count": 7,
            "label": 'Woche'
        }
        ]
    )
chartlayout = dict(
    autosize=True,
    height=350,
    width=600,
    title="Wähle einen Messpunkt auf der map",
    yaxis=dict(
        title="Passanten"
        ),
    xaxis=dict(
        title="Zeitpunkt",
        rangeselector = selectorOptions,
        )
    )

chart = dcc.Loading(
    type="default",
    children=[
        dcc.Graph(
            id='chart',
            config=config_plots,
            className="timeline-chart",
            figure={
                'data': [{
                    "x" : [],
                    "y" : [],
                    "mode":'lines+markers',
                    }],
                'layout': chartlayout
            })
        ])
# GEOIP BOX
lookup_span_default = "?"
geojs_lookup_div = html.Div(className="lookup",children=[
    html.H3("Automatische Standortsuche"),
    html.P('Sie können Ihren Standort automatisch bestimmen lassen. Klicken Sie dazu "Meinen Standort bestimmen" und erlauben Sie Ihrem Browser auf Ihren Standort zuzugreifen.'),
    html.Button(id='geojs_lookup_button', n_clicks=0, children='Meinen Standort bestimmen'),
    html.Pre(children=["Ihr Standort: ",html.Span(id="geojs_lookup_span",children=lookup_span_default)]),
    ])
    
# LOOKUP BOX
nominatim_lookup_div = html.Div(className="lookup",children=[
    html.H3("Manuelle Standortsuche"),
    dcc.Input(id="nominatim_lookup_edit", type="text", placeholder="", debounce=False),
    html.Button(id='nominatim_lookup_button', n_clicks=0, children='Suchen'),
    html.Pre(children=[
        "Ihr Standort: ",
        html.Span(id="nominatim_lookup_span",children=lookup_span_default),
        " ",
        html.Span(id="nominatim_lookup_span_adress",children=lookup_span_default),
        ]),
    ])

# AREA DIV
SLIDER_MAX = 120
area_div = html.Div(className="area lookup",id="area",children=[
    html.H3("Wählen Sie einen Radius"),
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
    html.H3("Durchnittlicher 7-Tage-Trend im gewählten Bereich:"),
    html.P(id="mean_trend_p",style={},children=[
        html.Span(id="mean_trend_span",children=""),
        "%"
        ])
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
    [Input('map', 'hoverData')],
    [State('chart', 'figure'),
     State('map', 'figure')])
def display_hover_data(hoverData,fig_chart,fig_map):
    #print("Hover",hoverData,type(hoverData))
    title="Wähle einen Datenpunkt auf der Karte!"
    times=[]
    values=[]
    if hoverData: #only for datapoints (trace 0), not for other elements
        curveNumber=hoverData["points"][0]['curveNumber']
        if fig_map["data"][curveNumber]["name"]==main_map_name:
            i=hoverData["points"][0]['pointIndex']
            title = f"{metadata.iloc[i]['city']} ({metadata.iloc[i]['name']})"
            station_id = metadata.iloc[i]["station_id"]
            #title = metadata.apply(lambda x: x["city"]+" ("+x["name"]+")",axis=1)
            times, values = queries.load_timeseries(query_api,station_id)
    fig_chart["data"][0]["x"]=times
    fig_chart["data"][0]["y"]=values
    fig_chart["layout"]["title"]=title
    return fig_chart

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
     Input('nominatim_lookup_span', 'children')],
    [State('hidden_latlon', 'children'),
     State('nominatim_lookup_span_adress', 'children')]
    )
def update_hidden_latlon(geojs_str,nominatim_str,hidden_latlon,nom_adress):
    ctx = dash.callback_context
    if not ctx.triggered:
        return ""
    input_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if input_id=="geojs_lookup_span":
        return geojs_str
    elif input_id=="nominatim_lookup_span" and nom_adress!="":
        return nominatim_str
    else:
        return hidden_latlon # original value, don't change

# Update map on geolocation change
@app.callback(
    [Output('map', 'figure'),
    Output('mean_trend_span','children')],
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
    
    filtered_metadata,poly=filter_by_radius(metadata,lat,lon,radius)
    mean_trend = round(filtered_metadata["trend"].mean(),1)
    #std_trend = filtered_metadata["trend"].std()
    
    x,y=poly.exterior.coords.xy
    fig["data"][0]["lat"]=y
    fig["data"][0]["lon"]=x
    return fig, str(mean_trend)


@app.callback(
    Output('mean_trend_p','style'),
    [Input('mean_trend_span','children')])
def style_mean_trend(mean_str):
    color = helpers.trend2color(float(mean_str))
    return dict(background=color)

@app.callback(
    [Output('nominatim_lookup_span', 'children'),
     Output('nominatim_lookup_span_adress', 'children')],
    [Input('nominatim_lookup_button', 'n_clicks'),
     Input('nominatim_lookup_edit', 'n_submit')],
    [State('nominatim_lookup_edit','value')])
def nominatim_lookup_callback(button,submit,query):
    return nominatim_lookup(query)

@cache.memoize(unless=DISABLE_CACHE) 
def nominatim_lookup(query):
    geolocator = Nominatim(user_agent="everyonecounts")
    geoloc = geolocator.geocode(query,exactly_one=True)
    if geoloc:
        lat=geoloc.latitude
        lon=geoloc.longitude
        address=geoloc.address
    else:
        address = ""
        lat = default_lat
        lon = default_lon
    return (str(lat)+", "+str(lon),address)
        

# MAIN
# ==================
if __name__ == '__main__':
    print("Let's go")
    
    # start Dash webserver
    app.layout = html.Div([
        hidden_latlon,
        title,
        area_div,
        nominatim_lookup_div,
        geojs_lookup_div,
        mainmap,
        #textbox,
        chart
    ])
    app.run_server(debug=True, host="localhost")
    