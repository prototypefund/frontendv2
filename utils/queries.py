"""
utility functions for the frontend that query the InfluxDB
"""
import datetime
import pandas as pd
import geopandas as gpd
from influxdb_client import InfluxDBClient


def get_query_api(url, org, token):
    # set up InfluxDB query API
    client = InfluxDBClient(url=url, token=token, org=org)
    return client.query_api()


def load_metadata(query_api, bucket="sdd"):
    """
    Return a GeoDataFrame with all tags and latitude/longitude fields
    """
    query = f'''
    from(bucket: "{bucket}")
    |> range(start: -10d) 
    |> filter(fn: (r) => r["_field"] == "lon" or r["_field"] == "lat")
    |> group(columns:["lat", "lon"])
    |> keep(columns: ["_field","_value","_id","_measurement"])
    |> unique()
    '''
    tables = query_api.query_data_frame(query)

    # pivot table so that the lat/lon fields become named columns
    geo_table = tables[["_field", "_value", "_id","_measurement"]].drop_duplicates()
    geo_table["_id"] = geo_table.apply(lambda x: x["_measurement"]+"_"+str(x["_id"]), axis=1)
    geo_table = geo_table.pivot(index='_id', columns='_field', values='_value')
    geo_table = round(geo_table, 5)

    # get trend value for each station
    trend = load_trend(query_api)

    # join everything together
    tables = tables.set_index("_id").join(trend).join(geo_table).reset_index()

    # drop unnecessary columns
    for column in tables.columns:
        if str(column).startswith("_") or str(column) == "result":
            tables.drop(column, inplace=True, axis=1)

    # Convert into GeoDataFrame
    tables = gpd.GeoDataFrame(tables, geometry=gpd.points_from_xy(tables.lon, tables.lat))

    return tables


def load_trend(query_api, bucket="sdd"):
    """ 
    calculate trend 
    value of 0.2 means 20% more acitivity than 7 days ago
    """
    query = f'''
    import "influxdata/influxdb/v1"
    v1.tagValues(bucket: "{bucket}", tag: "_time")
    |> sort()
    |> last()
    '''
    last_data_date = query_api.query_data_frame(query)["_value"][0]
    last_data_date = datetime.datetime.fromtimestamp(last_data_date.timestamp())

    last_data_date = last_data_date - datetime.timedelta(days=2)
    lastweek_data_date = last_data_date - datetime.timedelta(days=8)
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: {lastweek_data_date.strftime("%Y-%m-%d")})
      |> filter(fn: (r) => r["_measurement"] == "hystreet")
      |> filter(fn: (r) => r["_field"] == "pedestrian_count")
      |> filter(fn: (r) => r["unverified"] == "False")
      |> first()
    '''
    lastweek = query_api.query_data_frame(query)

    query = f'''
    from(bucket: "{bucket}")
      |> range(start: {last_data_date.strftime("%Y-%m-%d")})
      |> filter(fn: (r) => r["_measurement"] == "hystreet")
      |> filter(fn: (r) => r["_field"] == "pedestrian_count")
      |> filter(fn: (r) => r["unverified"] == "False")
      |> last()
    '''
    current = query_api.query_data_frame(query)
    current = current[["_id", "_value"]].rename(columns={"_value": "current"}).set_index("_id")
    lastweek = lastweek[["_id", "_value"]].rename(columns={"_value": "lastweek"}).set_index("_id")
    df = current.join(lastweek)

    def rate(current, lastweek):
        delta = current - lastweek
        if lastweek == 0:
            return None
        else:
            return 100 * round(delta / lastweek, 2)

    df["trend"] = df.apply(lambda x: rate(x["current"], x["lastweek"]), axis=1)
    return df["trend"]


def load_timeseries(query_api, _id, bucket="sdd"):
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -60d) 
      |> filter(fn: (r) => r["_measurement"] == "hystreet")
      |> filter(fn: (r) => r["_field"] == "pedestrian_count")
      |> filter(fn: (r) => r["_id"] == "{_id}")
      |> filter(fn: (r) => r["unverified"] == "False")
      '''
    tables = query_api.query_data_frame(query)
    times = list(tables["_time"])
    values = list(tables["_value"])
    return times, values
