"""
Test Dash leaflet
Docs: https://dash-leaflet.herokuapp.com/
Install with pip install dash-leaflet

Pros: 
    - Native support for geolocation (no fiddling with JS)
    - Clickable Map
    - Marker Groups
Cons:
    - Not very thourough documentation
Open questions:
    
    
"""

import pandas as pd
import dash
import dash_html_components as html
import dash_leaflet as dl
from dash_leaflet import express as dlx
from dash.dependencies import Input, Output
import requests

def load_data():
    df = pd.DataFrame()
    webcamurl="https://github.com/socialdistancingdashboard/SDD-Webcam/raw/master/webcam_list.json"
    dfweb=pd.read_json(webcamurl)
    dfweb=dfweb.rename(columns={"Lat":"lat","Lon":"lon","Name":"name"})
    dfweb["Typ"]="Webcam"
    df=df.append(dfweb[["Typ","name","lat","lon"]])

    csvurl = "https://github.com/socialdistancingdashboard/SDD-Aggregator/raw/master/data/stations_with_ags.csv"
    dfhystreet=pd.read_csv(csvurl)
    dfhystreet["Typ"]="Hystreet"
    df=df.append(dfhystreet[["Typ","name","lat","lon"]])

    csvurl = "https://github.com/socialdistancingdashboard/SDD-Bikecounter/raw/master/Counterlist-DE.csv"
    dfbike=pd.read_csv(csvurl,sep="\t")
    dfbike["Typ"]="Fahrräder"
    dfbike=dfbike.rename(columns={"nom":"name"})
    df=df.append(dfbike[["Typ","name","lat","lon"]])
    return df.reset_index()
df = load_data()

def typ2color(typ):
    if typ=="Webcam":
        return "red"
    elif typ=="Hystreet":
        return "blue"
    elif typ=="Fahrräder":
        return "green"
    else:
        return "black"

markers = [dl.CircleMarker(id="marker_"+str(i), children=dl.Tooltip(str(row["name"])), center=[row.lat,row.lon], color=typ2color(row.Typ)) for i,row in df.iterrows()]

# geojson test
def get_style(feature):
    return dict(fillColor="yellow", weight=2, opacity=1, color='red', dashArray='3', fillOpacity=0)
geojson_url = "https://github.com/isellsoap/deutschlandGeoJSON/raw/master/2_bundeslaender/3_mittel.geo.json"
r = requests.get(geojson_url)
geodata = r.json()
options = dict(hoverStyle=dict(weight=5, color='#666', dashArray=''), zoomToBoundsOnClick=True)
geojson = dlx.geojson(geodata, id="geojson", defaultOptions=options, style=get_style)


app = dash.Dash(prevent_initial_callbacks=True)
app.layout = html.Div([
    html.H1("Dash Leaflet Test"),
    html.P(id="text"),
    dl.Map([
        # dl.TileLayer(),  # <-- default basemap
        dl.TileLayer(url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png"),
        geojson,
        dl.LayerGroup(id="layer"), 
        dl.LocateControl(options={'locateOptions': {'enableHighAccuracy': True}}),
        dl.LayerGroup(id="drawing",children=markers),
        ],
    id="map", style={'width': '100%', 'height': '80vh', 'margin': "auto", "display": "block"}),
])

# Callback: Click on marker
@app.callback(
    Output("text", "children"), 
    [Input(marker.id, "n_clicks") for marker in markers])
def map_click_marker(*data):
    marker_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
    return "Hello from {}".format(marker_id)

# Callback: Click on map
@app.callback(
    Output("layer", "children"), 
    [Input("map", "click_lat_lng")])
def map_click_basemap(click_lat_lng):
    return [dl.Marker(position=click_lat_lng, children=dl.Tooltip("(Hier geklickt: {:.3f}, {:.3f})".format(*click_lat_lng)))]


if __name__ == '__main__':
    app.run_server(debug=True)