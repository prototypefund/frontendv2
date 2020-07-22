"""
utility functions for the frontend
"""

from math import isnan, log
from datetime import timedelta
from numpy import nan


def trend2color(trendvalue, alpha=1):
    """
    return a color code for a given trend value
    """
    if isnan(trendvalue):
        return f"rgba(180, 180, 180, {alpha})"
    elif trendvalue > 1:  # +100%
        # red
        return f"rgba(230, 0, 0, {alpha})"
    elif trendvalue < 0.2:  # +20%
        # green
        return f"rgba(0, 230, 50, {alpha})"
    else:
        # yellow
        return f"rgba(230, 200, 0, {alpha})"


def tooltiptext(df):
    """
    generate texts list for map hoverinfo
    """
    cols = sorted(df.columns)

    def make_string(df):
        s = ""
        for col in cols:
            s += "{}: {}<br>".format(str(col).capitalize(), str(df[col]))
        return s

    return list(df.apply(lambda x: make_string(x), axis=1))


fieldnames = {
        "airquality": "airquality_score",
        "bikes": "bike_count",
        "google_maps": "current_popularity",
        "hystreet": "pedestrian_count",
        "webcam": "personenzahl",
        "webcam-customvision": "personenzahl"
    }


def measurement2field(measurement):
    """
    Return the name of the field that contains the
    main data for each measurement type
    """
    return fieldnames[measurement]


def dash_callback_get_prop_ids(ctx):
    """
    needs dash dash.callback_context object aquired from a callback via ctx = dash.callback_context
    returns list of prop_ids
    see https://dash.plotly.com/advanced-callbacks for more info
    """
    return [x['prop_id'].split('.')[0] for x in ctx.triggered]


def calc_zoom(lat, lon):
    """
    Calculate zoom level based feature extent
    Input: list of lat and lon values
    Returns: Zoom level, center latitude, center longitude
    See also: https://stackoverflow.com/questions/46891914/control-mapbox-extent-in-plotly-python-api
    Not perfect, but good enough
    """
    lat = [x for x in lat if x is not None]
    lon = [x for x in lon if x is not None]
    width_y = max(lat) - min(lat)
    width_x = max(lon) - min(lon)
    centerlat = min(lat) + width_y / 2
    centerlon = min(lon) + width_x / 2
    zoom_y = -1.446*log(width_y) + 7.2753
    zoom_x = -1.415*log(width_x) + 8.7068
    return min(round(zoom_y,2),round(zoom_x,2)), centerlat, centerlon


def apply_model_fit(df, model, trend_window):
    """
    Add a column "fit" to a DataFrame with a "_time" column
    For this, apply linear regression with model parameters a (slope) and
    b (offset) to the unixtimestamp value of "_time". Do this only
    for values inside the trend_window
    """
    a, b = model
    day0 = max(df["_time"]) - timedelta(days=trend_window - 1)
    df["fit"] = nan
    df.loc[df["_time"] >= day0, "fit"] = df[df["_time"] >= day0].apply(lambda x: a * int(x["_time"].timestamp()) + b, axis=1)
    return df


