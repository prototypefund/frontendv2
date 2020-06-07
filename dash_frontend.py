import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import pandas as pd
from influxdb_client import InfluxDBClient
import numpy as np

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

    geo_table = tables[["_field","_value","station_id"]]
    geo_table = geo_table.pivot(index='station_id', columns='_field', values='_value')
    geo_table = round(geo_table,5)
    geo_dict = geo_table.to_dict("index")

    info_table = tables[['station_id','ags', 'bundesland', 'city', 'landkreis', 'name']]
    info_dict = info_table.set_index("station_id").drop_duplicates().to_dict("index")
    return geo_dict,info_dict

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

#  Dash Map
map=dcc.Graph(
    id='Karte',
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
                #color=list(df.apply(lambda x: colordict[x.Typ], 1))
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
                    lat=50,
                    lon=10
                    ),
                pitch=0,
                zoom=6,
                )
            )
    }
)
# LINE CHART
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
        'layout': {
            "autosize":True,
            "height":300,
            "width":600
            }
    })

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


@app.callback(
    Output('chart', 'figure'),
    [Input('Karte', 'hoverData')])
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
        times, values = load_timeseries(station_id)
        #times=[0,1,2]
        #values=[0,5,6]
    figure={
        'data': [{
            "x" : times,
            "y" : values,
            "mode":'lines',
            }],
        'layout': {
            "autosize":True,
            "height":350,
            "width":600,
            "title":title,
            }
    }
    return figure


if __name__ == '__main__':
    print("Let's go")
    
    # start Dash webserver
    app.layout = html.Div([
        title,
        map,
        #textbox,
        chart
    ])
    app.run_server(debug=True, host="localhost")
    
    
