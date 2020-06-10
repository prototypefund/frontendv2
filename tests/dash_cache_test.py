import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from flask_caching import Cache
import time

app = dash.Dash()
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache',
    'CACHE_THRESHOLD' : 4
    })
# see https://pythonhosted.org/Flask-Caching/
#app.config.suppress_callback_exceptions = True

app.layout = html.Div(
        style={'backgroundColor': "#eee","padding":10,"font-family":"monospace"}, 
        children=[
            html.H2(["Input"]),
            dcc.Slider(
                id='slider',
                min=0,
                max=20,
                step=1,
                value=10,
                tooltip=dict(
                    always_visible = False,
                    placement = "top"
                ),
                marks = {2*x:str(2*x) for x in range(11)}
            ),
            html.H2(["Output"]),
            dcc.Loading(
                id="loading",
                type="default",
                children=html.P(id='page-content',style={"font-weight":"bold","color":"green","background":"#ddd","padding":20}),
            )
            ]

        )


@app.callback(Output('page-content', 'children'),
             [Input('slider', 'value')])
@cache.memoize(timeout=30)  # in seconds
def update_url(value):
    time.sleep(2)
    print(value)
    return "The slidervalue is "+str(value)+'!'

# tips: try @cache.cached instead of memoize. Always returns the same
# value as no input is stored. Only use for functions without input



if __name__ == '__main__':
    app.run_server(debug=True, host="localhost")
    
