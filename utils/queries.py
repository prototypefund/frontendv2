'''
utility functions for the frontend
'''
import datetime
import pandas as pd
import geopandas as gpd
from influxdb_client import InfluxDBClient


def get_query_api(credentialsfile='credentials.txt'):
    # set up InfluxDB query API
    with open(credentialsfile,'r') as f:
        lines = f.readlines()
        url   = lines[0].rstrip()
        token = lines[1].rstrip()
        org   = lines[2].rstrip()
    client = InfluxDBClient(url=url, token=token, org=org)
    return client.query_api()

def load_metadata(query_api):
    """
    Return a GeoDataFrame with all tags and latitude/longitude fields
    """
    query = '''
        from(bucket: "test-hystreet")
      |> range(start: -10d) 
      |> filter(fn: (r) => r["_measurement"] == "hystreet")
      |> filter(fn: (r) => r["_field"] == "lon" or r["_field"] == "lat")
      |> drop(columns: ["unverified"])
      |> unique()
      |> yield(name: "unique")
      '''
    tables = query_api.query_data_frame(query)
    
    # pivot table so that the lat/lon fields become named columns
    geo_table = tables[["_field","_value","station_id"]].drop_duplicates()
    geo_table = geo_table.pivot(index='station_id', columns='_field', values='_value')
    geo_table = round(geo_table,5)
    
    # get trend value for each station
    trend  = load_trend(query_api)
    
    # join everything together
    tables = tables.set_index("station_id").join(trend).join(geo_table).reset_index()
    
    # drop unnecessary columns
    for column in tables.columns:
        if str(column).startswith("_") or str(column)=="result":
            tables.drop(column,inplace=True,axis=1)
    
    # Convert into GeoDataFrame
    tables = gpd.GeoDataFrame(tables, geometry=gpd.points_from_xy(tables.lon, tables.lat))
            
    return tables

def load_trend(query_api):
    """ 
    calculate trend 
    value of 0.2 means 20% more acitivity than 7 days ago
    """
    query = '''
    import "influxdata/influxdb/v1"
    v1.tagValues(bucket: "test-hystreet", tag: "_time")
    |> last()
    '''
    last_data_date = query_api.query_data_frame(query)["_value"][0]
    last_data_date = datetime.datetime.fromtimestamp(last_data_date.timestamp())
    
    last_data_date = last_data_date - datetime.timedelta(days=1)
    lastweek_data_date = last_data_date - datetime.timedelta(days=7)
    query='''
    from(bucket: "test-hystreet")
      |> range(start: {})
      |> filter(fn: (r) => r["_measurement"] == "hystreet")
      |> filter(fn: (r) => r["_field"] == "pedestrians_count")
      |> filter(fn: (r) => r["unverified"] == "False")
      |> first()
    '''.format(lastweek_data_date.strftime("%Y-%m-%d"))
    lastweek = query_api.query_data_frame(query)
    
    query = '''
    from(bucket: "test-hystreet")
      |> range(start: {})
      |> filter(fn: (r) => r["_measurement"] == "hystreet")
      |> filter(fn: (r) => r["_field"] == "pedestrians_count")
      |> filter(fn: (r) => r["unverified"] == "False")
      |> last()
    '''.format(last_data_date.strftime("%Y-%m-%d"))
    current = query_api.query_data_frame(query)
    current=current[["station_id","_value"]].rename(columns={"_value":"current"}).set_index("station_id")
    lastweek=lastweek[["station_id","_value"]].rename(columns={"_value":"lastweek"}).set_index("station_id")
    df = current.join(lastweek)
    def rate(current,lastweek):
        delta = current-lastweek
        if lastweek == 0:
            return None
        else:
            return 100*round(delta/lastweek,2)
    df["trend"] = df.apply(lambda x: rate(x["current"],x["lastweek"]), axis=1)
    return df["trend"]

def load_timeseries(query_api,station_id):
    query = '''
    from(bucket: "test-hystreet")
      |> range(start: -14d) 
      |> filter(fn: (r) => r["_measurement"] == "hystreet")
      |> filter(fn: (r) => r["_field"] == "pedestrians_count")
      |> filter(fn: (r) => r["station_id"] == "{}")
      |> filter(fn: (r) => r["unverified"] == "False")
      '''.format(station_id)
    tables = query_api.query_data_frame(query)
    times  = list(tables["_time"])
    values = list(tables["_value"])
    return times, values


