import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import pandas as pd
import json
import plotly.express as px
import requests

with open("../utils/geofeatures-ags-germany/counties.json", "r") as f:
    counties = json.load(f)

response = requests.get('https://im6qye3mc3.execute-api.eu-central-1.amazonaws.com/prod')
jsondump = response.json()["body"]
key = list(jsondump.keys())[0]
df = pd.DataFrame(jsondump[key]).T
df = df["hystreet_score"].dropna().reset_index()
df["index"] = df["index"].astype(str)
df["hystreet_score"] = df["hystreet_score"].astype(float)
print(df.head())

cmap = go.Choroplethmapbox(geojson=counties,
                           locations=df["index"],
                           z=df["hystreet_score"],
                           colorscale="Viridis",
                           zmin=0,
                           zmax=1,
                           marker_opacity=1,
                           marker_line_width=1)
app = dash.Dash()
app.layout = html.Div(children=[
    html.H1(
        children='Choropleth Test',
        style={
            'textAlign': 'center',
        }
    ),
    dcc.Graph(
        id='Karte',
        figure={
            'data': [
                cmap
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
    app.run_server(debug=True, port=8080, host="localhost")

