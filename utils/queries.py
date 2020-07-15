"""
utility functions for the frontend that query the InfluxDB
"""
import datetime
import pandas as pd
import numpy as np
import geopandas as gpd
from influxdb_client import InfluxDBClient
import json
from utils import helpers
from datetime import timedelta


def get_query_api(url, org, token):
    # set up InfluxDB query API
    client = InfluxDBClient(url=url, token=token, org=org)
    return client.query_api()


CID_SEP = "$"  # separator symbol for compound index


def compound_index(df):
    # make compound index
    return df.apply(lambda x: x["_measurement"] + CID_SEP + str(x["_id"]), axis=1)


def get_map_data(query_api, trend_window=3, bucket="sdd"):
    """
    Load the data that is required for plotting the map.
    Return a GeoDataFrame with all tags and latitude/longitude fields and the trend
    """
    fields = ["_field",
              "_value",
              "_id",
              "_measurement",
              "name",
              "ags",
              "bundesland",
              "landkreis",
              "city",
              "name",
              "districtType",
              "origin"]
    query = f'''
    from(bucket: "{bucket}")
    |> range(start: -10d) 
    |> filter(fn: (r) => r["_field"] == "lon" or r["_field"] == "lat")
    |> group(columns:["lat", "lon"])
    |> keep(columns: {json.dumps(fields)})
    '''
    tables = query_api.query_data_frame(query)
    tables.drop_duplicates(inplace=True)
    tables["c_id"] = compound_index(tables)
    # pivot table so that the lat/lon fields become named columns
    geo_table = tables[["_field", "_value", "c_id"]]
    geo_table = geo_table.pivot(index='c_id', columns='_field', values='_value')
    geo_table = round(geo_table, 6)
    geo_table = gpd.GeoDataFrame(geo_table, geometry=gpd.points_from_xy(geo_table.lon, geo_table.lat))

    # append metadata (name, ags, bundesland, etc...)
    metadata = tables.drop(columns=["result", "table", "_value", "_field"], errors="ignore")
    metadata = metadata.set_index("c_id").drop_duplicates()
    geo_table = geo_table.join(metadata)

    # get trend value for each station
    # trend = load_trend(query_api)

    # join everything together
    # tables = tables.set_index("_id").join(trend).join(geo_table).reset_index()

    geo_table = geo_table.reset_index()
    trenddict, models = load_trend(query_api, trend_window)
    geo_table["trend"] = geo_table["c_id"].map(trenddict)
    geo_table["model"] = geo_table["c_id"].map(models)

    # def applyfit(row):
    #     if row["_id"] in models:
    #         a, b = models[row["_id"]]
    #         return a * row["unixtime"] + b
    #     else:
    #         return np.nan
    # geo_table["fit"] = geo_table.apply(lambda x: applyfit(x), axis=1)

    print("Result of 'get_map_data():")
    print(geo_table.columns)
    print(geo_table["_measurement"].value_counts())

    return geo_table


def load_trend(query_api, trend_window=3, bucket="sdd"):
    print("load_trend...")
    filterstring = " or ".join([f'r["_field"] == "{x}"' for x in helpers.fieldnames.values()])
    query = f'''
            from(bucket: "{bucket}")
          |> range(start: -{trend_window}d)
          |> filter(fn: (r) =>  {filterstring})
          '''
    tables = query_api.query_data_frame(query)
    df = pd.concat(tables)
    df["c_id"] = compound_index(df)
    models = {}
    trend = {}
    df["unixtime"] = df["_time"].apply(lambda x: int(x.timestamp()), 1)  # unixtime in s
    for idx in set(df["c_id"]):
        # get sub-dataframe for this id
        tmpdf = df[df["c_id"] == idx].sort_values(by=["unixtime"])
        # remove too old data
        lastday = max(tmpdf["_time"])
        day0 = lastday - timedelta(days=trend_window-1)
        tmpdf = tmpdf[tmpdf["_time"] >= day0]
        tmpdf = tmpdf.reset_index(drop=True)

        firstday = min(tmpdf["_time"])
        # note: day0 is the (theoretical) beginning of the trend window
        #       and firstday is the (actual) first day where data is available

        if (lastday - firstday).days < trend_window-1:
            # not enough data for this station
            models[idx] = (np.nan, np.nan)
            trend[idx] = np.nan
            continue

        # linear regression y = a*x +b
        values = pd.to_numeric(tmpdf["_value"])
        model = np.polyfit(tmpdf["unixtime"], values, 1)
        a, b = model
        models[idx] = model

        # calculate trend
        #
        t1 = firstday.timestamp()
        t2 = lastday.timestamp()
        y1 = (a * t1 + b)
        y2 = (a * t2 + b)
        if y1 > 0:
            trend[idx] = y2 / y1 - 1
        else:
            trend[idx] = np.nan

    return trend, models  # dict


def load_timeseries(query_api, c_id, bucket="sdd"):
    """
    Load time series for a given compound index
    """
    print("load_timeseries", c_id)
    _measurement, _id = c_id.split(CID_SEP, 1)
    _field = helpers.measurement2field(_measurement)
    extra_lines = ''
    if _measurement == "hystreet":
        extra_lines += '|> filter(fn: (r) => r["unverified"] == "False")\n'
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -60d) 
      |> filter(fn: (r) => r["_measurement"] == "{_measurement}")
      |> filter(fn: (r) => r["_field"] == "{_field}")
      |> filter(fn: (r) => r["_id"] == "{_id}")
      {extra_lines}
      '''
    tables = query_api.query_data_frame(query)
    times = []
    values = []
    rolling = []
    if isinstance(tables, list):
        tables = tables[0]
    if not isinstance(tables, pd.DataFrame):
        print(f"Warning: tables type is not DataFrame but {type(tables)} (load_timeseries)")
    elif tables.empty:
        print(f"Warning: No data for {c_id} (load_timeseries)")
    else:
        times = list(tables["_time"])
        values = list(tables["_value"])
        rolling = tables.set_index("_time")["_value"].rolling("3d").mean()

    return times, values, rolling
