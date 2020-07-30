import dash_core_components as dcc
import dash_html_components as html
from utils import helpers

SLIDER_MAX = 130


def main_controls(map_data, CONFIG):
    TRENDWINDOW = CONFIG["TRENDWINDOW"]
    MEASUREMENTS = CONFIG["measurements"]
    landkreis_options = [{'label': x, 'value': x} for x in sorted(map_data["landkreis_label"].unique())]
    bundesland_options = [{'label': x, 'value': x} for x in sorted(map_data["bundesland"].unique())]

    return html.Div(id="main_controls", children=[
        html.Img(id="title",
                 className="container",
                 src="assets/logo.png",
                 alt="EveryoneCounts - Das Social Distancing Dashboard"),
        html.Div(id="detail_container", className="container", children=[
            html.H3("Detailgrad"),
            dcc.RadioItems(
                id="detail_radio",
                options=[
                    {'label': 'Punkte', 'value': 'stations'},
                    {'label': 'Landkreise', 'value': 'landkreis'},
                    {'label': 'Bundesländer', 'value': 'bundesland'}
                ],
                value='stations',
                labelStyle={'display': 'inline-block'}
            ),
            html.H3("Datenquellen"),
            dcc.Checklist(
                id="trace_visibility_checklist",
                options=[
                    {'label': helpers.measurementtitles[key], 'value': key}
                    for key in helpers.measurementtitles
                    if key in MEASUREMENTS
                ],
                value=['hystreet', 'webcam-customvision', 'bikes'],
                labelStyle={'display': 'block'}
            ),
        ]),
        html.Div(id="trend_container", className="container", children=[
            html.Div(children=[
                html.H3(f"{TRENDWINDOW}-Tage-Trend im gewählten Bereich"),
                html.P(id="mean_trend_p", style={}, children=[
                    html.Span(id="mean_trend_span", children="")
                ]),
            ]),
            html.P(id="location_p", children=[
                html.P(id="location_text", children="?"),
                html.Button(children="Ändern ↓"),
            ]),
        ]),
        html.Div(id="region_container", className="container", children=[
            dcc.Tabs(id='region_tabs', className="", value='tab-umkreis', children=[
                dcc.Tab(label='Umkreis', value='tab-umkreis', children=[
                    html.Div(id="radius_search_tab", children=[
                        html.H3("Mittelpunkt bestimmen:"),
                        html.Div(id="search-container", children=[
                            dcc.Input(id="nominatim_lookup_edit", type="text", placeholder="", debounce=False),
                            html.Button(id='nominatim_lookup_button', n_clicks=0, children='Suchen'),
                        ]),
                        html.Button(id='geojs_lookup_button', n_clicks=0, children='Automatisch bestimmen'),
                        html.Button(id='mapposition_lookup_button', n_clicks=0, children='Kartenmittelpunkt verwenden'),
                        html.H3("Umkreis:"),
                        dcc.Slider(
                            id='radiusslider',
                            min=5,
                            max=SLIDER_MAX,
                            step=5,
                            value=60,
                            tooltip=dict(
                                always_visible=False,
                                placement="top"
                            ),
                            marks={20 * x: str(20 * x) + 'km' for x in range(SLIDER_MAX // 20 + 1)}
                        )
                    ]),
                ]),
                dcc.Tab(label='Landkreis', value='tab-landkreis', children=[
                    html.H3("Wähle einen Landkreis:"),
                    dcc.Dropdown(
                        id='landkreis_dropdown',
                        options=landkreis_options,
                        value=landkreis_options[0]["value"],
                        clearable=False
                    ),
                    html.P("Hinweis: Nur Landkreise mit Datenpunkten können ausgewählt werden!"),
                ]),
                dcc.Tab(label='Bundesland', value='tab-bundesland', children=[
                    html.H3("Wähle ein Bundesland:"),
                    dcc.Dropdown(
                        id='bundesland_dropdown',
                        options=bundesland_options,
                        value=bundesland_options[0]["value"],
                        clearable=False
                    ),
                ]),
            ])
        ]),
        html.Div(id="footer", className="footer", children=[
            html.P([
                html.Span("EveryoneCounts 2020"),
                html.A(children="Impressum", href="https://blog.everyonecounts.de/impressum/", target="_blank"),
                html.A(children="Blog", href="https://blog.everyonecounts.de/", target="_blank"),
                html.A(children="Kontakt", href="mailto:kontakt@everyonecounts.de", target="_blank"),
                html.A(children="Twitter", href="https://twitter.com/_everyonecounts", target="_blank"),
                html.A(children="Github", href="https://github.com/socialdistancingdashboard/", target="_blank"),
                html.A(id="permalink", children="Permalink", href="xyz"),
            ]),
        ])
    ])


def mainmap():
    default_lat = 50
    default_lon = 10
    config_plots = dict(
        locale="de-DE",
        displaylogo=False,
        modeBarButtonsToRemove=['lasso2d',
                                'toggleSpikelines',
                                'toggleHover',
                                'select2d',
                                'autoScale2d',
                                'resetScale2d',
                                'resetViewMapbox'],
        displayModeBar=True,
        responsive=True
    )

    #  Dash Map
    return dcc.Graph(
        id='map',
        config=config_plots,
        figure={
            'data': [],
            'layout': dict(
                autosize=True,
                hovermode='closest',
                showlegend=False,
                legend_title_text='Datenquelle',
                legend=dict(
                    x=0.5,
                    y=1,
                    traceorder="normal",
                    font=dict(
                        family="sans-serif",
                        size=14,
                        color="black"
                    ),
                    bgcolor="#fff",
                    bgopacity=0.3,
                    bordercolor="#eee",
                    borderwidth=1
                ),
                # height=400,
                margin=dict(l=0, r=0, t=0, b=0),
                mapbox=dict(
                    style="carto-positron",
                    # open-street-map,
                    # white-bg,
                    # carto-positron,
                    # carto-darkmatter,
                    # stamen-terrain,
                    # stamen-toner,
                    # stamen-watercolor
                    bearing=0,
                    center=dict(
                        lat=default_lat,
                        lon=default_lon
                    ),
                    pitch=0,
                    zoom=6,
                )
            ),
        },
    )


def storage():
    # dcc Storage
    return [
        dcc.Store(id='clientside_callback_storage', storage_type='memory'),
        dcc.Store(id='nominatim_storage', storage_type='memory'),
        dcc.Store(id='urlbar_storage', storage_type='memory'),
        dcc.Store(id='highlight_polygon', storage_type='memory'),
        dcc.Store(id='latlon_local_storage', storage_type='local'),
    ]


def timeline_chart():
    return html.Div(id="chart-container", style={'display': 'none'}, children=[
        html.Button(id="chart-close", children=" × "),
        dcc.Loading(
            id="timeline-chart",
            type="circle",
            children=[
                dcc.Checklist(id="timeline-avg-check", value=[])
                # This checklist  needs to be in the layout because
                # a callback is bound to it. Otherwise, Dash 1.12 will throw errors
                # This is an issue even when using app.validation_layout or
                # suppress_callback_exceptions=True, as suggested in the docs
                # Don't trust the documentation in this case.
            ]
        ),
    ])
