"""
utility functions for the frontend that query the InfluxDB
"""
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

    geo_table = geo_table.reset_index()
    trenddict, models = load_trend(query_api, trend_window)
    geo_table["trend"] = geo_table["c_id"].map(trenddict)
    geo_table["model"] = geo_table["c_id"].map(models)

    print("Result of 'get_map_data():")
    print(geo_table.columns)
    print(geo_table["_measurement"].value_counts())

    return geo_table


def load_trend(query_api, trend_window=3, bucket="sdd"):
    """
    Acquire trend values for all stations
    this is an expensive call, as the data from all stations
    for the last trend_window days will be requested from
    the influxdb. It is highly recommended to cache this!

    Returns two dicts:
        trend: c_id -> trend value
        models: c_id -> (a, b)
    a and b are the linear regression fit parameters: a=slope, b=offset

    """
    print(f"load_trend... (trend_window={trend_window})")
    filterstring = " or ".join([f'r["_field"] == "{x}"' for x in helpers.fieldnames.values()])
    query = f'''
            from(bucket: "{bucket}")
          |> range(start: -{trend_window + 2}d)
          |> filter(fn: (r) =>  {filterstring})
          '''
    tables = query_api.query_data_frame(query)
    df = pd.concat(tables)
    df["c_id"] = compound_index(df)
    models = {}
    trend = {}
    df["unixtime"] = df["_time"].apply(lambda x: int(x.timestamp()), 1)  # unixtime in s
    for cid in set(df["c_id"]):
        # get sub-dataframe for this id
        tmpdf = df[df["c_id"] == cid].sort_values(by=["unixtime"])

        lastday = max(tmpdf["_time"])
        firstday = min(tmpdf["_time"])

        if (lastday - firstday).days < trend_window - 1:
            # not enough data for this station, trend window not covered
            models[cid] = (np.nan, np.nan)
            trend[cid] = np.nan
            continue

        day0 = lastday - timedelta(days=trend_window - 1)
        tmpdf = tmpdf[tmpdf["_time"] >= day0]
        tmpdf = tmpdf.reset_index(drop=True)

        values = pd.to_numeric(tmpdf["_value"])

        COUNT_LOW_THRESHOLD = 3
        PERCENT_NONZEROS_THRESHOLD = 0.75
        # perform linear regression only when the mean is above COUNT_LOW_THRESHOLD
        # or if the fraction of non-zero numbers exceeds PERCENT_NONZEROS_THRESHOLD.
        # This is to suppress unhelpful fits for low-value data sources
        if np.mean(values) > COUNT_LOW_THRESHOLD or \
                np.count_nonzero(values) / len(values) > PERCENT_NONZEROS_THRESHOLD:
            # linear regression y = a*x +b
            model = np.polyfit(tmpdf["unixtime"], values, 1)
            models[cid] = model

            # calculate trend
            a, b = model[:2]
            t1 = day0.timestamp()
            t2 = lastday.timestamp()
            y1 = (a * t1 + b)
            y2 = (a * t2 + b)
            if y1 > 0:
                trend[cid] = y2 / y1 - 1
            else:
                trend[cid] = np.nan
        else:
            # counts too low for reliable regression
            models[cid] = (np.nan, np.nan)
            trend[cid] = np.nan

    return trend, models  # dicts


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
    if isinstance(tables, list):
        tables = tables[0]
    assert isinstance(tables,
                      pd.DataFrame), f"Warning: tables type is not DataFrame but {type(tables)} (load_timeseries)"
    assert not tables.empty, f"Warning: No data for {c_id} (load_timeseries)"

    tables["rolling"] = tables.set_index("_time")["_value"].rolling("3d").mean().values
    # import ipdb
    # ipdb.set_trace()
    return tables[["_time", "_value", "rolling"]]
