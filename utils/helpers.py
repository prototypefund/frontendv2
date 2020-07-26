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


def tooltiptext(df, mode):
    """
    generate texts list for map hoverinfo
    unfortunately, styling needs to be done here
    because css class attributes are stripped by Dash
    """
    def format_trend_str(trend_float):
        if isnan(trend_float):
            return '<i>nicht verfügbar</i>'
        trend_str = str(round(100 * trend_float)) + '%'
        if trend_float > 0:
            trend_str = '+' + trend_str
        return trend_str
    if mode == "stations":
        def make_string(row):
            trend_str = format_trend_str(row['trend'])
            if row["city"] is None:
                title_str = row['name']
            else:
                title_str = f"{row['city']} ({row['name']})"
            s = (
                f"<span style='font-size:1.5em'><b>{title_str}</b></span><br>"
                f"<span style='font-size:0.85em; opacity:0.8;'>{row['landkreis']}, {row['bundesland']}</span><br>"
                f"<span style='font-size:0.85em; opacity:0.8;'>{row['_measurement']}</span><br>"
                f"<br><span style='font-size:1em'><b>Trend:</b></span>"
                f"<span style='font-size:1.5em'> {trend_str}</span>"
                )
            return s
    else:
        def make_string(row):
            trend_str = format_trend_str(row["trend"]["mean"])
            count = row["trend"]["count"]
            s = (
                f"<span style='font-size:1.5em'><b>{row[mode].to_string().strip()}</b></span><br>"
                f"<span style='font-size:0.85em; opacity:0.8;'>Messpunkte: {count}</span><br>"
                f"<span style='font-size:1em'><b>Durchschnittlicher Trend:</b></span>"
                f"<span style='font-size:1.5em'> {trend_str}</span>"
            )
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


