# Test of a very simple Dash app that opens a webserver
# serving a single page. The page consists of an interactive 
# mapbox map that shows some of our data sources.

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import pandas as pd

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
    return df

df = load_data()
df.marker = "bus"
colordict = {"Webcam":"red","Fahrräder":"green","Hystreet":"blue"}


app = dash.Dash()
colors = {
    'background': '#fff',
    'text': '#339'
}
app.layout = html.Div(style={'backgroundColor': colors['background']}, children=[
    html.H1(
        children='Hello Dash',
        style={
            'textAlign': 'center',
            'color': colors['text']
        }
    ),
    html.Div(children='Dash: A web application framework for Python.', style={
        'textAlign': 'center',
        'color': colors['text']
    }),
    dcc.Graph(
        id='Karte',
        figure={
            'data': [
                go.Scattermapbox(
                lat=df.lat,
                lon=df.lon,
                mode='markers+text',
                marker=go.scattermapbox.Marker(
                    size=12, 
                    color=list(df.apply(lambda x: colordict[x.Typ], 1))
                    ),
                text=list(df.apply(lambda x: x["Typ"]+": "+x["name"],1))
                )
            ],
            'layout': go.Layout(
                        autosize=True,
                        mapbox_style="open-street-map",
                        hovermode='closest',
                        height=768,
                        mapbox=dict(
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
])

if __name__ == '__main__':
    print("Let's go")
    app.run_server(debug=True)
    
