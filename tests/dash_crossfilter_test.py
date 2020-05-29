# See https://dash.plotly.com/interactive-graphing

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import numpy as np

app = dash.Dash(__name__)

# generate some dummy data
Ngeo = 50
Ndummy = 90
datax = np.linspace(0,100,Ndummy)
datay = [np.random.random(Ndummy) for x in range(Ngeo)]
text = ['Punkt '+str(x) for x in range(Ngeo)]

# MAP
map = dcc.Graph(
        id='Karte',
        figure={
            'data': [{
                "type": "scattermapbox",
                "lat" : np.round(40+20*np.random.random(Ngeo),2),
                "lon" : np.round(10+20*np.random.random(Ngeo),2),
                "mode":'markers',
                "marker":dict(
                    size=12, 
                    color='red'
                    ),
                "text":text
                }],
            'layout': {
                        "autosize":True,
                        "hovermode":'closest',
                        "height":500,
                        "mapbox":dict(
                            style="carto-darkmatter",
                            # open-street-map, white-bg, carto-positron, carto-darkmatter, stamen-terrain, stamen-toner, stamen-watercolor
                            center=dict(
                                lon=20,
                                lat=50,
                                ),
                            zoom=3
                            )
                        }
        })

# LINE CHART
chart = dcc.Graph(
        id='chart',
        figure={
            'data': [{
                "x" : 40+20*np.random.random(50),
                "y" :10+20*np.random.random(50),
                "mode":'lines',
                }],
            'layout': {
                        "autosize":True,
                        "height":300,
                        "width":600
                        }
        })

textbox = html.Div(className='row', children=[
        html.Div([
            dcc.Markdown("""
                **Datenauswahl**
                
                Mouse over values in the map.
            """),
            html.Pre(id='hover-data')
        ])

    ])

app.layout = html.Div([
    map,
    chart,
    textbox
])


@app.callback(
    [Output('hover-data', 'children'),
    Output('chart', 'figure')],
    [Input('Karte', 'hoverData')])
def display_hover_data(hoverData):
    print("Hover",hoverData,type(hoverData))
    if hoverData==None:
        text = "Hover is NONE"
        title="Nothing to see here"
        x=[]
        y=[]
    else:
        i=hoverData["points"][0]['pointIndex']
        text = "Selected: "+str(i)
        title = hoverData["points"][0]['text']
        x=datax
        y=datay[i]
    figure={
        'data': [{
            "x" : x,
            "y" : y,
            "mode":'lines',
            }],
        'layout': {
                    "autosize":True,
                    "height":300,
                    "width":600,
                    "title":title,
                    }
    }
    return text,figure

if __name__ == '__main__':
    app.run_server(debug=True, host="localhost")