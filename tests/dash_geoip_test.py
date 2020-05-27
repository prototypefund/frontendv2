   
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

app = dash.Dash(__name__)

app.layout = html.Div([
    html.Button(id='thebutton', n_clicks=0, children='Localize!'),
    html.Div(id='my-div')
])

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
    Output(component_id='my-div', component_property='children'),
    [Input(component_id='thebutton', component_property='n_clicks')]
)


if __name__ == '__main__':
    app.run_server(debug=True)