"""
Helper function to get outline coordinates for bundesland or landkreis

Use local GeoJSON files from https://github.com/m-ad/geofeatures-ags-germany
Alternatively, get them from github by web request:
    import requests
    url_bl = "https://github.com/m-ad/geofeatures-ags-germany/raw/master/geojson/states.json"
    url_lk = "https://github.com/m-ad/geofeatures-ags-germany/raw/master/geojson/counties.json"
    geojson_bl = requests.get(url_bl).json()
    geojson_lk = requests.get(url_lk).json()
"""


import json

if __name__ == '__main__':
    file_lk = "geofeatures-ags-germany/counties.json"
    file_bk = "geofeatures-ags-germany/states.json"
else:
    file_lk = "utils/geofeatures-ags-germany/counties.json"
    file_bk = "utils/geofeatures-ags-germany/states.json"

with open(file_lk, "r") as f:
    geojson_lk = json.load(f)
with open(file_bk, "r") as f:
    geojson_bl = json.load(f)




def get_outline_coords(type, ags):
    """
    Helper function to get outline coordinates for bundesland or landkreis
    type: either "bundesland" or "landkreis"
    ags: Amtlicher Gemeindeschlüssel , e.g. "08212"
    """
    if type == "bundesland":
        geojson = geojson_bl
    elif type == "landkreis":
        geojson = geojson_lk
    else:
        raise NameError
    coords = None
    for feature in geojson["features"]:
        if int(feature["id"]) == int(ags):
            if feature["geometry"]["type"] == "MultiPolygon":
                coords = []
                for sublist in feature["geometry"]["coordinates"]:
                    for item in sublist[0]:
                        coords.append(item)
                    coords.append([None, None])  # prevent connection line beetween individual polygons
            else:
                # normal polgygon
                coords = feature["geometry"]["coordinates"][0]
            break
    if coords is not None:
        x, y = list(zip(*coords))
        return x, y
    else:
        print(f"WARNING get_coords: AGS {ags} not found!")
        return None, None


if __name__ == '__main__':
    # RUN TEST
    print('get_outline_coords("bundesland", "04")')
    print(get_outline_coords("bundesland", "04"))
    print("---------------------")
    print('get_outline_coords("landkreis", "08221")')
    print(get_outline_coords("landkreis", "08221"))
    print("---------------------")
    print('get_outline_coords("landkreis", "123456789")')
    print('Expectation: "AGS 123456789 not found"')
    print(get_outline_coords("landkreis", "123456789"))