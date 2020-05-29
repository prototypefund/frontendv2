# Test of a very simple Dash app that opens a webserver
# serving a single page. The page consists of an interactive 
# mapbox map that shows some of our data sources.

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output


app = dash.Dash()

app.layout = html.Div(
        style={'backgroundColor': "#eee","padding":10}, 
        children=[
            dcc.Location(id='url', refresh=False),
            html.H1(
                children='URL Parameter Test',
                style={
                    'textAlign': 'center',
                }
            ),
            dcc.Markdown("""
                **Datenauswahl**
                
                Change the Urlbar, e.g. add [/banana](banana) or [/whatever](whatever) to the end
                Mouse over values in the map.
            """),
            html.Div(id='page-content',style={"font-weight":"bold","color":"red"}),
            dcc.Slider(
                id='slider',
                min=0,
                max=20,
                step=1,
                value=10,
            ),
            #dcc.Link('Roll the dice!', href='/page-2'),
            ]

        )


@app.callback(Output('url', 'search'),
             [Input('slider', 'value')])
def update_url(value):
    return "?slider="+str(value)

@app.callback(
                Output('page-content', 'children'),
                [ Input('url', 'pathname'),
                  Input('url', 'search') 
                ]
             )
def display_page(pathname,search):
    a = html.P('pathname: "{}"'.format(pathname))
    if search==None:
        b=html.P('search: None')
    else:
        b=html.P('search: "{}"'.format(search))
    return html.Div([a,b])
        
  



if __name__ == '__main__':
    app.run_server(debug=True, host="localhost")
    
