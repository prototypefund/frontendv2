import dash_core_components as dcc
import dash_html_components as html
from utils import helpers
from utils.ec_analytics import tracking_pixel_img
from numpy import nan

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
        html.Div(id="info_container", className="container", children=[
            html.Button(id="btn-info", children="Informationen anzeigen ↓"),
            html.Div(id="infotext", style={"display": "none"}, children=[
                html.H3("Informationen über diese Karte"),
                dcc.Markdown(f"""
                Die Maßnahmen gegen COVID-19 wie Kontaktverbote und geschlossene Geschäfte haben große 
                Änderungen in unserem Alltag mit sich gebracht. Wir sehen dies jeden Tag wenn wir vor die Haustür 
                gehen. Aber wie ist die Lage im Rest des Landes? Wird Social Distancing überall gleich strikt 
                befolgt? Sinkt die Zurückhaltung am Wochenende oder bei guten Wetter? Sind tatsächlich mehr/weniger 
                Menschen im Park unterwegs? Diese Fragen sind sehr schwer direkt zu beantworten, aber wir können 
                versuchen, **indirekt** Erkentnisse darüber zu gewinnen indem wir verschiedene Indikatoren 
                zur **Aktivität im öffentlichen Raum** betrachten. Dazu setzen wir auf unterschiedliche Datenquellen, 
                um ein möglichst umfassendes Bild zu zeichnen. 
                
                Die Punkt auf der Karte stellen einzelne Messtationen dar. Die Farbe entspricht dem aktuellen
                **{TRENDWINDOW}-Tage-Trend**:"""),
                html.Div(id="legende", children=[
                    html.Div(id="legende-1",
                             style={"background": helpers.trend2color(-1.)},
                             children="fallend oder gleich (< +10%)"),
                    html.Div(id="legende-2",
                             style={"background": helpers.trend2color(0.3)},
                             children="leicht steigend (+10% bis +100%) "),
                    html.Div(id="legende-3",
                             style={"background": helpers.trend2color(2.0)},
                             children="stark steigend (> +100%)"),
                    html.Div(id="legende-4",
                             style={"background": helpers.trend2color(nan)},
                             children="zu wenig Daten für die Trendbestimmung"),
                ]),
                dcc.Markdown(f"""Du kannst auf jede Station klicken um mehr 
                Informationen zu erhalten. Außerdem kannst Du den **Detailgrad** ändern um verschiedene Landkreise oder 
                Bundesländer mit einander zu vergleichen. In der "Punkte"-Ansicht kannst Du den Trend über die 
                Mess-Stationen in deiner Umgebung (hellblauer Bereich auf der Karte) mitteln lassen. Diesen Bereich 
                kannst Du über eine Umkreis-Auswahl oder mit der Landkreis- oder Bundesland-Suche weiter unten im Menü 
                festlegen.
                """),
                html.H3("Weitere Informationen"),
                html.Ul([
                    html.Li(html.A(children="Über das Projekt",
                                   href="https://blog.everyonecounts.de/das-projekt/",
                                   target="_blank")),
                    html.Li(html.A(children="Über das Team",
                                   href="https://blog.everyonecounts.de/das-team/",
                                   target="_blank")),
                    html.Li(html.A(children="Über die Daten",
                                   href="https://blog.everyonecounts.de/die-daten/",
                                   target="_blank")),
                    html.Li(html.A(children="Presseberichte",
                                   href="https://blog.everyonecounts.de/presseschau/",
                                   target="_blank")),
                    html.Li(html.A(children="Blog",
                                   href="https://blog.everyonecounts.de/",
                                   target="_blank")),
                ]),
                html.Div(id="supporter", children=[
                    html.A(href="https://bmbf.de",
                           className="supporter",
                           target="_blank",
                           children=[
                               html.Img(src="assets/support_bmbf.png")
                           ]),
                    html.A(href="https://projecttogether.org/wirvsvirus/",
                           className="supporter",
                           target="_blank",
                           children=[
                               html.Img(src="assets/support_solutionenabler.png")
                           ]),
                ]),
                html.Button(id="btn-info-close", children="Informationen ausblenden ↑"),
            ])
        ]),
        html.Div(id="btn-main-toolbar-container", className="container", children=[
            html.Button(id="btn-main-toolbar", children="Optionen anzeigen ↓"),
        ]),
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
                value=MEASUREMENTS,
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
                html.Span(id="location_text", children="?"),
            ]),
            html.Button(id="btn-region-select", children="Region auswählen ↓"),
            html.Div(id="region_container",
                     style={"display": "none"},
                     children=[
                         dcc.Tabs(id='region_tabs', className="", value='tab-umkreis', children=[
                             dcc.Tab(label='Umkreis', value='tab-umkreis', children=[
                                 html.Div(id="radius_search_tab", children=[
                                     html.H3("Mittelpunkt bestimmen:"),
                                     html.Div(id="search-container", children=[
                                         dcc.Input(id="nominatim_lookup_edit", type="text", placeholder="",
                                                   debounce=False),
                                         html.Button(id='nominatim_lookup_button', n_clicks=0, children='Suchen'),
                                     ]),
                                     html.Button(id='geojs_lookup_button', n_clicks=0,
                                                 children='Automatisch bestimmen'),
                                     html.Button(id='mapposition_lookup_button', n_clicks=0,
                                                 children='Kartenmittelpunkt verwenden'),
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
        ]),
        html.Div(id="footer-container", children=[
            html.Div(id="footer", className="footer", children=[
                html.P([
                    html.Span("EveryoneCounts 2020"),
                    html.A(children="Impressum", href="https://blog.everyonecounts.de/impressum/", target="_blank"),
                    html.A(children="Blog", href="https://blog.everyonecounts.de/", target="_blank"),
                    html.A(children="Widgets", href="https://everyonecounts.de/widget/configurator", target="_blank"),
                    html.A(children="Kontakt", href="mailto:kontakt@everyonecounts.de", target="_blank"),
                    html.A(children="Twitter", href="https://twitter.com/_everyonecounts", target="_blank"),
                    html.A(children="Github", href="https://github.com/socialdistancingdashboard/", target="_blank"),
                    #  html.A(id="permalink", children="Permalink", href="xyz"),
                ]),
            ]),
        ]),
        tracking_pixel_img()
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
        dcc.Store(id='latlon_local_storage', storage_type='local', data=(50.144, 8.617, "Frankfurt am Main")),
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


def feedback_window():
    return html.Div(id="feedback-container", style={'display': 'block'}, children=[
        html.Button(id="feedback-close", children=" × "),
        dcc.Markdown(
            """
            Hast Du **3 Minuten Zeit** für unsere kleine **Nutzerbefragung**? Wir möchten besser werden und 
            EveryoneCounts weiterentwickeln, dafür ist Feedback von unseren Nutzern von unschätzbarem Wert. Hilf mit!
            """),
        html.A(children=">> Link zur Umfrage (Google Forms) <<",
               target="_blank",
               href="https://docs.google.com/forms/d/e/1FAIpQLSda91f1ewYx2y-Z7GOK8FqffThDIxUMe1OJ0bWaC0EuRiMxcA/viewform")
    ])
