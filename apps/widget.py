import json
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from urllib.parse import parse_qs

from utils import queries, timeline_chart, helpers
from utils.cached_functions import load_timeseries, load_last_datapoint
from app import app

# READ CONFIG
# ===========
with open("config.json", "r") as f:
    CONFIG = json.load(f)
TRENDWINDOW = CONFIG["TRENDWINDOW"]


# INITIALIZE CHART OBJECT
# ================
CHART = timeline_chart.TimelineChartWindow(TRENDWINDOW, load_timeseries)

layout = html.Div(id="widget", children=[
    dcc.Location(id='url-widget', refresh=True),
    html.Div(id="widget-container"),
    html.Div(id="ec-attribution", children=[
        "Bereitgestellt von ",
        html.A(
            id="ec_link",
            children="EveryoneCounts",
            href="https://everyonecounts.de",
            target="_blank")
    ])
])


@app.callback(
    Output('widget-container', 'children'),
    [Input('url-widget', 'search')]
)
def build_widget(url_search_str):
    urlparams = {}
    if url_search_str is not None:
        urlparams = parse_qs(url_search_str.replace("?", ""))
    if "widgettype" not in urlparams:
        return "You need to specify a widgettype. Either timeline or fill."
    elif "station" not in urlparams:
        return "You need to specify a station. Use the configurator."
    widgettype = urlparams["widgettype"][0]
    c_id = urlparams["station"][0]
    last = load_last_datapoint(c_id)
    if last.empty:
        return f"No data for station {c_id}"
    if widgettype == "timeline":
        show_trend = False  # default
        show_rolling = True  # default
        if "show_trend" in urlparams:
            show_trend = urlparams["show_trend"] == ["1"]
        if "show_rolling" in urlparams:
            show_rolling = urlparams["show_rolling"] == ["1"]
        CHART.update_figure("stations", c_id, last, False, [], show_trend, show_rolling)
        return CHART.get_timeline_window(show_api_text=False)
    elif widgettype == "fill":
        measurement, _id = queries.split_compound_index(c_id)
        unit = helpers.measurementtitles[measurement]
        last_value = float(last["_value"])
        last_time = helpers.utc_to_local(last["_time"].iloc[0])
        last_time = last_time.strftime(helpers.timeformats[measurement])
        name = last['name'].iloc[0]
        show_number = "total"  # default
        if 'city' in last.columns:
            city = last['city'].iloc[0]
            if city is not None and type(city) is str:
                name = f"{city} ({name})"
        flex_container = []
        if "trafficlight" in urlparams and urlparams["trafficlight"] == ["1"]:
            if "t1" in urlparams and "t2" in urlparams:
                t1 = int(urlparams["t1"][0])
                t2 = int(urlparams["t2"][0])
                imgsrc = "../assets/ampel/"
                if t1 is None or t2 is None:
                    return "Thresholds t1 and t2 need to be integers"
                if last_value > t2:
                    imgsrc += "ampel_r.png"  # red
                    alt = "rote Ampel"
                elif last_value > t1:
                    imgsrc += "ampel_y.png"  # yellow
                    alt = "gelbe Ampel"
                else:
                    imgsrc += "ampel_g.png"  # green
                    alt = "grüne Ampel"
                flex_container.append(
                    html.Div(children=[
                        html.Img(id="trafficlight",
                                 alt=alt,
                                 src=imgsrc)]))
            else:
                return "No thresholds defined (t1 and t2)"
        fill_text_output = []
        if "max" in urlparams:
            max_value = int(urlparams["max"][0])
            percentage = round(100 * last_value / max_value, 0)
            if "show_number" in urlparams and urlparams["show_number"][0] in ["total", "percentage", "both"]:
                show_number = urlparams["show_number"][0]
            fill_text_output.append(html.Div(id="widget-percentage",
                                             className=f"{show_number} {widgettype}",
                                             children=f"{round(percentage)}%"))
            fill_text_output.append(html.Div(id="widget-total",
                                             className=f"{show_number} {widgettype}",
                                             children=f"{last_value} / {max_value}"))
            # Hiding of the percentage value in case of show_number=="total" is done via CSS
        else:
            fill_text_output.append(html.Div(id="widget-total",
                                             className=f"{show_number} {widgettype}",
                                             children=last_value))
        fill_text_output.append(html.Div(id="widget-unit",
                                         className=f"{show_number} {widgettype}",
                                         children=f"{unit}"))
        fill_text_output.append(html.Div(id="widget-time",
                                         className=f"{show_number} {widgettype}",
                                         children=last_time,
                                         ))
        fill_text_output.append(html.Div(id="widget_origin",
                                         children=[
                                             "Datenquelle: ",
                                             html.A(
                                                 children=helpers.originnames[measurement],
                                                 href=last["origin"].tolist()[0],
                                                 target="_blank")
                                         ])
                                )
        flex_container.append(html.Div(children=fill_text_output))
        output = [
            html.H1(id="widget-title", children=name),
            html.Div(id="flex_container", children=flex_container)
        ]

        return output
    else:
        return "Unknown widgettype"


@app.callback(
    Output('widget', 'style'),
    [Input('url-widget', 'search')]
)
def set_widget_width(url_search_str):
    # noinspection PyBroadException
    try:
        urlparams = parse_qs(url_search_str.replace("?", ""))
        width = int(urlparams["width"][0])
        width = width - 2 * 16  # subtract padding and border
        return {"width": width}
    except:
        return dash.no_update
