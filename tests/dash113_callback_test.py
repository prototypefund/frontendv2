"""
MWE to highlight the issue with Dash 1.13 that callback execution has changed

https://community.plotly.com/t/how-to-separate-parallel-callbacks-nested-elements-in-dash-1-13/43163

When the button is pressed, I want to show the info box. When the background is
clicked, I want to hide the infobox. Simple. This code would have worked in
Dash 1.12, because back then, the callback was executed once only and prop_ids was
a list of all callbacks ([“button”, “div”] when clicking on the button and [“div”]
when clicking on the div).

However, since 1.13, dash behaves differently. The callback function is now
executed twice, one time for the button callback and one time for the div.
This makes it impossible to figure out which one was actually pressed.
"""

import dash
import dash_html_components as html
from dash.dependencies import Input, Output

app = dash.Dash()
app.layout = html.Div(id="div", style={"background": "yellow", "padding": "200px"}, children=[
    html.Button(id="button", children="show infotext"),
    html.Div(id="info", children="INFOTEXT", style={"display": "none"})
])


@app.callback(
    Output("info", "style"),
    [Input("div", "n_clicks"),
     Input("button", "n_clicks")],
)
def test(div, btn):
    ctx = dash.callback_context
    print("Callback", ctx.triggered)
    prop_ids = [x['prop_id'].split('.')[0] for x in ctx.triggered]
    if "button" in prop_ids:
        print("Action: show")
        return {"display": "block"}
    else:
        print("Action: hide")
        return {"display": "none"}

app.run_server(debug=True)
