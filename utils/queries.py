"""
utility functions for the frontend that query the InfluxDB
"""
import pandas as pd
import numpy as np
import geopandas as gpd
from influxdb_client import InfluxDBClient
import json
import logging
from utils import helpers
from datetime import timedelta, datetime


def get_query_api(url, org, token):
    # set up InfluxDB query API
    client = InfluxDBClient(url=url, token=token, org=org)
    return client.query_api()


CID_SEP = "$"  # separator symbol for compound index


def compound_index(df):
    # make compound index
    return df.apply(lambda x: x["_measurement"] + CID_SEP + str(x["_id"]), axis=1)


def get_map_data(query_api, measurements, trend_window=3, bucket="sdd"):
    """
    Load the data that is required for plotting the map.
    Return a GeoDataFrame with all tags and latitude/longitude fields and the trend
    """
    logging.debug("Influx DB query for get_map_data()")
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
              "origin",
              "start_date",
              "end_date"]
    geo_table = pd.DataFrame()
    tables = pd.DataFrame()
    required_columns = {"_id", "ags", "bundesland", "districtType", "landkreis", "name", "origin"}
    for _measurement in measurements:
        query = f'''
        from(bucket: "{bucket}")
        |> range(start: -10d) 
        |> filter(fn: (r) => r["_field"] == "lon" or r["_field"] == "lat")
        |> filter(fn: (r) => r["_measurement"] == "{_measurement}")
        |> filter(fn: (r) => r["unverified"] != "True")
        |> group(columns:["lat", "lon"])
        |> keep(columns: {json.dumps(fields)})
        '''
        try:
            logging.debug(f" Influx query for {_measurement}...")
            influx_table = query_api.query_data_frame(query)
        except:
            print("Error fetching data from influxdb")
            print(query)
            continue
        influx_table.drop_duplicates(inplace=True)

        columns = set(influx_table.columns)
        if not required_columns.issubset(columns):
            missing = required_columns.difference(columns)
            print(f"Missing columns for {_measurement}: {missing}")
            logging.warning(f"Missing columns for {_measurement}: {missing}")
            continue

        if _measurement == "webcam-customvision":
            influx_table = helpers.filter_by_consent(influx_table)
        elif _measurement == "writeapi":
            now = datetime.now()
            influx_table["start_date"] = pd.to_datetime(influx_table["start_date"])
            influx_table["end_date"] = pd.to_datetime(influx_table["end_date"])
            # remove inactive events:
            influx_table = influx_table[influx_table["end_date"] >= now]
            influx_table = influx_table[influx_table["start_date"] <= now]
        if influx_table.empty:
            continue

        influx_table["c_id"] = compound_index(influx_table)
        influx_table["_value"] = pd.to_numeric((influx_table["_value"]))
        if tables.empty:
            tables = influx_table.copy()
        else:
            tables = tables.append(influx_table, ignore_index=True)
    # pivot table so that the lat/lon fields become named columns
    geo_table = tables[["_field", "_value", "c_id"]]
    geo_table = geo_table.astype({'_value': 'float'})
    geo_table = geo_table.pivot_table(index='c_id', columns='_field', values='_value')
    geo_table = round(geo_table, 6)
    geo_table = gpd.GeoDataFrame(geo_table, geometry=gpd.points_from_xy(geo_table.lon, geo_table.lat))

    # append metadata (name, ags, bundesland, etc...)
    metadata = tables.drop(columns=["result", "table", "_value", "_field"], errors="ignore")
    metadata = metadata.set_index("c_id").drop_duplicates()
    geo_table = geo_table.join(metadata)

    geo_table = geo_table.reset_index()
    geo_table["ags"] = geo_table["ags"].str.zfill(5)  # 1234 --> "01234"
    trenddict = load_trend(query_api, measurements, trend_window)
    geo_table["trend"] = geo_table["c_id"].map(trenddict["trend"])
    geo_table["model"] = geo_table["c_id"].map(trenddict["model"])
    geo_table["last_value"] = geo_table["c_id"].map(trenddict["last_value"])
    geo_table["last_time"] = geo_table["c_id"].map(trenddict["last_time"])
    geo_table["landkreis_label"] = geo_table.apply(lambda x: str(x["landkreis"]) + " " + str(x["districtType"]), 1)

    print("Result of 'get_map_data():")
    print(geo_table.dtypes)
    print("\nNumber of stations:")
    print(geo_table["_measurement"].value_counts())

    logging.info(f'Number of stations:\n{geo_table["_measurement"].value_counts()}')

    return geo_table


def load_trend(query_api, measurements, trend_window=3, bucket="sdd"):
    """
    Acquire trend values for all stations
    this is an expensive call, as the data from all stations
    for the last trend_window days will be requested from
    the influxdb. It is highly recommended to cache this!

    Returns a dict of dict with the following keys:
        trend : trend value
        model : parameter tupel (a, b)
        last_value : last value
        last_time  : datetime
    Each of these contains a dict with c_id -> value
    Example:
        > x = load_trend(...)
        > x['model']['some_id']
        (1.234, 5.678)

    a and b are the linear regression fit parameters: a=slope, b=offset

    """
    print(f"load_trend... (trend_window={trend_window})")
    logging.debug(f"Influx DB query for load_trend() with trend_window={trend_window}")
    filterstring = " or ".join([f'r["_field"] == "{helpers.fieldnames[x]}"' for x in measurements])
    query = f'''
            from(bucket: "{bucket}")
          |> range(start: -{trend_window + 2}d)
          |> filter(fn: (r) =>  {filterstring})
          |> filter(fn: (r) => r["unverified"] != "True")
          '''
    tables = query_api.query_data_frame(query)
    print("query executed")
    df = pd.concat(tables)
    df["c_id"] = compound_index(df)

    output = {
        "model": {},
        "trend": {},
        "last_value": {},
        "last_time": {}
    }
    df["_time"] = df["_time"].apply(helpers.utc_to_local, 1)
    df["unixtime"] = df["_time"].apply(lambda x: int(x.timestamp()), 1)  # unixtime in s
    for cid in set(df["c_id"]):
        # get sub-dataframe for this id

        tmpdf = df[df["c_id"] == cid].sort_values(by=["unixtime"])
        output["last_value"][cid] = tmpdf["_value"].iloc[-1]
        output["last_time"][cid] = tmpdf["_time"].iloc[-1]

        lastday = max(tmpdf["_time"])
        firstday = min(tmpdf["_time"])

        if (lastday - firstday).days < trend_window - 1:
            # not enough data for this station, trend window not covered
            output["model"][cid] = (np.nan, np.nan)
            output["trend"][cid] = np.nan
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
            output["model"][cid] = model

            # calculate trend
            a, b = model[:2]
            t1 = day0.timestamp()
            t2 = lastday.timestamp()
            y1 = (a * t1 + b)
            y2 = (a * t2 + b)
            if y1 > 0:
                output["trend"][cid] = y2 / y1 - 1
            else:
                output["trend"][cid] = np.nan
        else:
            # counts too low for reliable regression
            output["model"][cid] = (np.nan, np.nan)
            output["trend"][cid] = np.nan

    return output  # dicts


def load_timeseries(query_api, c_id, daysback=90, bucket="sdd"):
    """
    Load time series for a given compound index
    """
    logging.debug(f"Influx DB query for load_timeseries(..., {c_id})")
    print("load_timeseries", c_id)
    _measurement, _id = c_id.split(CID_SEP, 1)
    _field = helpers.measurement2field(_measurement)
    extra_lines = ''
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -{daysback}d) 
      |> filter(fn: (r) => r["_measurement"] == "{_measurement}")
      |> filter(fn: (r) => r["_field"] == "{_field}")
      |> filter(fn: (r) => r["_id"] == "{_id}")
      |> filter(fn: (r) => r["unverified"] != "True")
      '''
    tables = query_api.query_data_frame(query)
    if isinstance(tables, list):
        tables = tables[0]
    assert isinstance(tables,
                      pd.DataFrame), f"Warning: tables type is not DataFrame but {type(tables)} (load_timeseries)"
    if tables.empty:
        print(f"Warning: No data for {c_id} (load_timeseries)")
        return None
    tables["_time"] = tables["_time"].apply(helpers.utc_to_local, 1)
    tables["rolling"] = tables.set_index("_time")["_value"].rolling("3d").mean().values
    # import ipdb
    # ipdb.set_trace()
    return tables[["_time", "_value", "rolling"]]
