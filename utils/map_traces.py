import json
import numpy as np
import pandas as pd
from utils import helpers
import plotly.graph_objects as go


def get_map_traces(map_data, measurements):
    """
    Prepare traces for the map Graph depending on the level of
    detail: "station", "landkreis", "bundesland"

    :param geopandas.GeoDataFrame map_data: map_data GeoDataFrame
    :param list measurements: list of measurements to include
    :return dict: dict of traces for plotting
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

    for measurement in measurements:
        measurement_map_data = map_data[map_data["_measurement"] == measurement]

        # geodataseries as return (lat, lon,...) can cause issues, convert to dataframe:
        measurement_map_data = pd.DataFrame(measurement_map_data)

        trace = dict(
            # TRACE 1...N: Datapoints
            _measurement=measurement,  # custom entry
            name=helpers.measurementtitles[measurement],
            type="scattermapbox",
            lat=list(measurement_map_data["lat"]),
            lon=list(measurement_map_data["lon"]),
            mode='markers',
            marker=dict(
                size=20,
                color=list(measurement_map_data.apply(lambda x: helpers.trend2color(x["trend"]), axis=1)),
                line=dict(width=2,
                          color='DarkSlateGrey'),
            ),
            text=helpers.tooltiptext(measurement_map_data, mode="stations"),
            hoverinfo="text",
            customdata=list(measurement_map_data["c_id"])
        )
        traces["stations"].append(trace)

    # Prepare landkreis/bundeslad choropleth maps
    choropleth_df_original = map_data.copy()
    choropleth_df_original = choropleth_df_original[choropleth_df_original["_measurement"].isin(measurements)]
    for region in ("landkreis", "bundesland"):
        choropleth_df = choropleth_df_original.copy()
        if region == "bundesland":
            choropleth_df["ags"] = choropleth_df["ags"].str[:-3]
            geojson_filename = "states.json"
        else:
            # landkreis
            geojson_filename = "counties.json"
        choropleth_df = choropleth_df.groupby(["ags", region]).agg(["mean", "size"]).reset_index()
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
    return traces
