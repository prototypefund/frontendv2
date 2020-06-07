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
    url,token,org = get_credentials()
    client = InfluxDBClient(url=url, token=token, org=org)
    query_api = client.query_api()
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

# Get data
geo_dict,info_dict = load_metadata()
station_ids = list(geo_dict.keys())


# Title
title=html.H1(
    children='EveryoneCounts',
    style={
        'textAlign': 'center',
        'color': "#333",
        'fontFamily':'Arial, Helvetica, sans-serif'
    }
)
    
#  Dash Map
map=dcc.Graph(
    id='Karte',
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
            text=[info_dict[x]["city"]+" ("+info_dict[x]["name"]+")" for x in station_ids],
            hoverinfo="text",
        )],
        'layout': dict(
            autosize=True,
            hovermode='closest',
            height=768,
            mapbox=dict(
                style="open-street-map", # open-street-map, white-bg, carto-positron, carto-darkmatter, stamen-terrain, stamen-toner, stamen-watercolor
                bearing=0, 
                center=dict(
                    lat=50,
                    lon=10
                    ),
                pitch=0,
                zoom=6
                )
            )
    }
)


textbox = html.Div(children=[
        html.Div([
            dcc.Markdown("""
                **Datenauswahl**
                
                Mouse over values in the map.
            """),
            html.Pre(id='textboxid')
        ])

    ])
app = dash.Dash()
app.layout = html.Div([
    title,
    map,
    textbox
    #chart,
    #textbox
])

@app.callback(
    Output('textboxid', 'children'),
    [Input('Karte', 'hoverData')])
def display_hover_data(hoverData):
    print("Hover",hoverData,type(hoverData))
    if hoverData==None:
        text = "Hover is NONE"
        title="Nothing to see here"
        print('blubb')
    else:
        i=hoverData["points"][0]['pointIndex']
        id = station_ids[i]
        #text = "Selected: "+str(i)

        text = str(info_dict[id])
        #print(id)
        #title = hoverData["points"][0]['text']
        #x=datax
        #y=datay[i]
    return text


if __name__ == '__main__':
    print("Let's go")
    app.run_server(debug=True)#, port=8080, host="localhost")
    
