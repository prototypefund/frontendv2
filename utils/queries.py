"""
utility functions for the frontend that query the InfluxDB
"""
import datetime
import pandas as pd
import geopandas as gpd
from influxdb_client import InfluxDBClient
import json
from utils import helpers

CID_SEP = "$"  # separator symbol for compound index

def get_query_api(url, org, token):
    # set up InfluxDB query API
    client = InfluxDBClient(url=url, token=token, org=org)
    return client.query_api()


def get_map_data(query_api, bucket="sdd"):
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
              "dictrictType",
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
    tables["c_id"] = tables.apply(lambda x: x["_measurement"] + CID_SEP + str(x["_id"]), axis=1)  # make compound index

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
    geo_table["trend"] = 0  # TODO: Re-insert Trend!

    print("Result of 'get_map_data():")
    print(geo_table["_measurement"].value_counts())

    return geo_table


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


def load_timeseries(query_api, c_id, bucket="sdd"):
    """
    Load time series for a given compound index
    """
    _measurement, _id = c_id.split(CID_SEP, 1)
    _field = helpers.measurement2field(_measurement)
    extra_lines = ''
    if _measurement=="hystreet":
        extra_lines+='|> filter(fn: (r) => r["unverified"] == "False")\n'
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -60d) 
      |> filter(fn: (r) => r["_measurement"] == "{_measurement}")
      |> filter(fn: (r) => r["_field"] == "{_field}")
      |> filter(fn: (r) => r["_id"] == "{_id}")
      {extra_lines}
      '''
    tables = query_api.query_data_frame(query)
    times = list(tables["_time"])
    values = list(tables["_value"])
    return times, values
