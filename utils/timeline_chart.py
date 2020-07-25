from utils import helpers
import dash_core_components as dcc
import dash_html_components as html


class TimelineChartWindow:

    def __init__(self, TRENDWINDOW, load_timeseries):
        self.load_timeseries = load_timeseries
        self.TRENDWINDOW = TRENDWINDOW
        self.origin_url = ""
        self.origin_str = ""
        self.mode = "stations"
        self.config_plots = dict(
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
        self.selectorOptions = dict(
            buttons=[
                {
                    "step": 'all',
                    "label": 'Gesamt'
                }, {
                    "step": 'year',
                    "stepmode": 'backward',
                    "count": 1,
                    "label": 'Jahr'
                }, {
                    "step": 'month',
                    "stepmode": 'backward',
                    "count": 3,
                    "label": '3 Monate'
                }, {
                    "step": 'month',
                    "stepmode": 'backward',
                    "count": 1,
                    "label": 'Monat'
                }, {
                    "step": 'day',
                    "stepmode": 'backward',
                    "count": 7,
                    "label": 'Woche'
                }
            ]
        )
        self.chartlayout = dict(
            autosize=True,
            height=350,
            width=700,
            title="Waehle einen Messpunkt auf der Karte",
            hovermode='closest',
            yaxis=dict(
                title="Passanten"
            ),
            xaxis=dict(
                title="Zeitpunkt",
                rangeselector=self.selectorOptions,
            ),
            legend=dict(
                orientation="h",
                y=-0.5
            )
        )
        self.figure = {
            'data': [],
            'layout': self.chartlayout
        }

    def get_figure(self):
        return self.figure

    def update_figure(self, detail_radio, clickData, map_data):

        curveNumber = clickData["points"][0]['curveNumber']
        pointIndex = clickData["points"][0]['pointIndex']
        if detail_radio == "landkreis" or detail_radio == "bundesland":
            location = clickData["points"][0]['location']
            if detail_radio == "landkreis":
                filtered_map_data = map_data[map_data["ags"] == location]
                figtitle = filtered_map_data.iloc[0]["landkreis"]
            else:
                filtered_map_data = map_data[map_data["ags"].str[:-3] == location]
                figtitle = filtered_map_data.iloc[0]["bundesland"]
            self.origin_url = ""
            self.origin_str = ""
            self.figure["data"] = []
            for c_id in filtered_map_data["c_id"].unique():
                df_timeseries = self.load_timeseries(c_id)
                name = filtered_map_data[filtered_map_data["c_id"] == c_id].iloc[0]["name"]
                trace = dict(  # datapoints
                    x=df_timeseries["_time"],
                    y=df_timeseries["_value"],
                    mode="lines+markers",
                    name=name,
                    line=dict(width=1),
                    marker=dict(
                        size=6,
                    ),
                )
                self.figure["data"].append(trace)
                self.figure["layout"]["yaxis"]["title"] = "Wert"
                self.figure["layout"]["title"] = figtitle

        elif detail_radio == "stations" and curveNumber > 0:  # exclude selection marker
            filtered_map_data = map_data[map_data["trace_index"] == curveNumber]
            city = filtered_map_data.iloc[pointIndex]['city']
            name = filtered_map_data.iloc[pointIndex]['name']
            if city is None:
                figtitle = f"{name}"
            else:
                figtitle = f"{city} ({name})"
            c_id = filtered_map_data.iloc[pointIndex]["c_id"]
            self.origin_url = filtered_map_data.iloc[pointIndex]["origin"]
            # origin_str = f"Datenquelle: {filtered_map_data.iloc[i]['_measurement']}"
            self.origin_str = f"Datenquelle: {c_id}"

            # Get timeseries data for this station
            df_timeseries = self.load_timeseries(c_id)

            # Add "fit" column based on model
            model = filtered_map_data.iloc[pointIndex]['model']
            df_timeseries = helpers.apply_model_fit(df_timeseries, model, self.TRENDWINDOW)

            self.figure["data"] = [
                dict(  # datapoints
                    x=df_timeseries["_time"],
                    y=df_timeseries["_value"],
                    mode="lines+markers",
                    name="Daten",
                    line=dict(color="#d9d9d9", width=1),
                    marker=dict(
                        size=6,
                        color="DarkSlateGrey",
                    ),
                ),
                dict(  # rolling average
                    x=df_timeseries["_time"],
                    y=df_timeseries["rolling"],
                    mode="lines",
                    line_shape="spline",
                    name="Gleitender Durchschnitt",
                    line=dict(color="#F63366", width=4),
                ),
                dict(  # fit
                    x=df_timeseries["_time"],
                    y=df_timeseries["fit"],
                    mode="lines",
                    name=f"{self.TRENDWINDOW}-Tage-Trend",
                    line=dict(color="blue", width=2),
                )]

            self.figure["layout"]["title"] = figtitle
        else:
            return False
        self.mode = detail_radio
        return True

    def get_timeline_window(self):
        output = []
        graph = dcc.Graph(
            id='chart',
            config=self.config_plots,
            className="timeline-chart",
            figure=self.figure
        )
        output.append(graph)
        if self.mode == "stations":
            origin = html.A(id="chart_origin", children=self.origin_str, href=self.origin_url)
            output.append(origin)
        else:
            checklist = dcc.Checklist(
                options=[
                    {'label': 'Fußgänger (Hystreet)', 'value': 'hystreet'},
                    {'label': 'Fußgänger (Webcams)', 'value': 'webcams'},
                    {'label': 'Fahrradfahrer', 'value': 'bikes'},
                    {'label': 'Popularität (Google)', 'value': 'google_maps'},
                    {'label': 'Luftqualität', 'value': 'airquality'}
                ],
                value=['hystreet', 'webcams', 'bikes', 'google_maps'],
                labelStyle={'display': 'block'}
            )
            output.append(checklist)
        return output
