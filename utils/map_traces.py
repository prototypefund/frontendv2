import json
import numpy as np
from utils import helpers
import plotly.graph_objects as go


def get_map_traces(map_data):
    """
    Prepare traces for the map Graph depending on the level of
    detail: "station", "landkreis", "bundesland"

    :param geopandas.GeoDataFrame map_data: map_data GeoDataFrame
    :return dict: dict of traces for plotting
    :return geopandas.GeoDataFrame: updated map_data GeoDataFrame
    """
    traces = dict()
    traces["stations"] = [dict(
        # TRACE 0: radius selection marker
        name="Filter radius",
        type="scattermapbox",
        fill="toself",
        showlegend=False,
        fillcolor="rgba(135, 206, 250, 0.3)",
        marker=dict(
            color="rgba(135, 206, 250, 0.0)",
        ),
        hoverinfo="skip",
        lat=[],
        lon=[],
        mode="lines"
        )]

    # Split into traces by measurement, add column "trace_index" (important for data selection)
    for index, measurement in enumerate(map_data["_measurement"].unique()):
        map_data.loc[map_data["_measurement"] == measurement, "trace_index"] = index+1
        measurement_map_data = map_data[map_data["_measurement"] == measurement]
        trace = dict(
            # TRACE 1...N: Datapoints
            _measurement=measurement,  # custom entry
            name=helpers.measurementtitles[measurement],
            type="scattermapbox",
            lat=measurement_map_data["lat"],
            lon=measurement_map_data["lon"],
            mode='markers',
            marker=dict(
                size=20,
                color=measurement_map_data.apply(lambda x: helpers.trend2color(x["trend"]), axis=1),
                line=dict(width=2,
                          color='DarkSlateGrey'),
            ),
            text=helpers.tooltiptext(measurement_map_data, mode="stations"),
            hoverinfo="text",
            customdata=measurement_map_data["c_id"]
        )
        traces["stations"].append(trace)
    map_data["trace_index"] = map_data["trace_index"].astype(int)

    # Prepare landkreis/bundeslad choropleth maps
    for region in ("landkreis", "bundesland"):
        choropleth_df = map_data.copy().dropna(subset=["trend"])
        if region == "bundesland":
            choropleth_df["ags"] = choropleth_df["ags"].str[:-3]
            geojson_filename = "states.json"
        else:
            # landkreis
            geojson_filename = "counties.json"
        choropleth_df = choropleth_df.groupby(["ags", region]).agg(["mean", "count"]).reset_index()
        with open(f"utils/geofeatures-ags-germany/{geojson_filename}", "r") as f:
            geojson = json.load(f)
        # noinspection PyTypeChecker
        traces[region] = [go.Choroplethmapbox(
            geojson=geojson,
            locations=choropleth_df["ags"],
            z=choropleth_df["trend"]["mean"],
            showlegend=False,
            showscale=False,
            colorscale=[helpers.trend2color(x) for x in np.linspace(-1, 2, 10)],
            hoverinfo="text",
            zmin=-1,
            zmax=2,
            text=helpers.tooltiptext(choropleth_df, mode=region),
            marker_line_color="white",
            marker_opacity=1,
            marker_line_width=1)]
    return map_data, traces
