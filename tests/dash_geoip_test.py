import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

app = dash.Dash(__name__)

fig={
'data': [
    go.Scattermapbox(
    lat=[0],
    lon=[0],
    mode='markers',
    marker=go.scattermapbox.Marker(size=12)
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
                    lat=0,
                    lon=0
                    ),
                pitch=0,
                zoom=12
                )
            )
}
map = dcc.Graph(id='karte',
                figure=fig)


app.layout = html.Div([
    html.Button(id='thebutton', n_clicks=0, children='Localize!'),
    html.Div(id='div1'),
    html.Div(id='div2'),
    map
])

@app.callback(
    Output('karte', 'figure'),
    [Input('div1', 'children')])
def update_figure(pos_str):
    lat,lon = pos_str.split(", ")
    mylat = float(lat)
    mylon = float(lon)
    
    fig={
    'data': [
        go.Scattermapbox(
        lat=[mylat],
        lon=[mylon],
        mode='markers',
        marker=go.scattermapbox.Marker(size=12)
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
                        lat=mylat,
                        lon=mylon
                        ),
                    pitch=0,
                    zoom=12
                    )
                )
    }
    
    return(fig)

app.clientside_callback(
    """
    function(x) {
        return getLocation();
        //return "client_"+x;
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
    Output(component_id='div1', component_property='children'),
    [Input(component_id='thebutton', component_property='n_clicks')]
)


if __name__ == '__main__':
    app.run_server(debug=True, port=8080, host="localhost")
    