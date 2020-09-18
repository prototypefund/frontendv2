"""
Function to filter a GeoDataFrame by a circle around a 
latitude/longitude point and a given radius
"""

from math import radians, degrees, cos, sin
from shapely.geometry import Polygon, Point
import geopandas as gpd


def get_bounding_box(lat=10, lon=52, radius_km=300):
    """
    Calculate a lat, lon bounding box around a
    centeral point with a given half-side distance or radius.
    Input and output lat/lon values specified in decimal degrees.
    Output: [lat_min,lon_min,lat_max,lon_max]
    """
    r_earth_km = 6371  # earth radius

    # convert to radians
    lat = radians(lat)
    lon = radians(lon)
    # everything is in radians from this point on

    # latitude
    delta_lat = radius_km / r_earth_km
    lat_max = lat + delta_lat
    lat_min = lat - delta_lat

    # longitude
    delta_lon = radius_km / (r_earth_km * cos(lat))
    lon_max = lon + delta_lon
    lon_min = lon - delta_lon

    return map(degrees, [lat_min, lon_min, lat_max, lon_max])


def filter_by_radius(gdf, lat, lon, radius):
    """
    gdf is a GeoDataFrame, lat/lon are in decimal degree
    and radius is in kilometers
    """
    lat1, lon1, lat2, lon2 = get_bounding_box(lat, lon, radius)
    spatial_index = gdf.sindex
    candidates = list(spatial_index.intersection([lon1, lat1, lon2, lat2]))
    gdf_box = gdf.reset_index(drop=True).loc[candidates]
    dlat = lat1 - lat2
    dlon = lon1 - lon2
    x = [lat + sin(radians(2 * x)) * dlat / 2 for x in range(0, 180)]
    y = [lon + cos(radians(2 * x)) * dlon / 2 for x in range(0, 180)]
    p = Polygon([(b, a) for a, b in zip(x, y)])
    return gdf_box[gdf_box.intersects(p)], p


if __name__ == '__main__':
    """ 
    Test: create a dummy dataframe with 3 entries and filter it
    Expected result: The filtered dataframe should consist of only 2 entries
    """
    print("== TEST ==")
    dummygdf = gpd.GeoDataFrame({"data": ["A", "B", "C"]}, geometry=[Point(0, 0), Point(3, 3), Point(1, 1)])
    print("ORIGINAL GEODATAFRAME:")
    print(dummygdf)
    filtered, _ = filter_by_radius(dummygdf, 0, 0, 300)
    print("\nFILTERED GEODATAFRAME:")
    print(filtered)
