"""
utility functions for the frontend
"""

from math import isnan, log
from datetime import timedelta
from numpy import nan
import pandas as pd
import logging
import pytz


def trend2color(trendvalue, alpha=1):
    """
    return a color code for a given trend value
    """
    if isnan(trendvalue):
        return f"rgba(180, 180, 180, {alpha * 0.7})"
    elif trendvalue > 1:  # +100%
        # red
        return f"rgba(230, 0, 0, {alpha})"
    elif trendvalue < 0.1:  # +10%
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
            if isnan(row["last_value"]):
                last_value = "nicht verfügbar"
            else:
                last_value = round(float(row["last_value"]), 1)
            try:
                last_time = row["last_time"].strftime("%d.%m.%Y %H:%M")
            except ValueError:
                last_time = ""
            trend_str = format_trend_str(row['trend'])
            if "city" in row and type(row["city"]) == str:
                title_str = f"{row['city']} ({row['name']})"
            else:
                title_str = row['name']
            s = (
                f"<span style='font-size:1.5em'><b>{title_str}</b></span><br>"
                f"<span style='font-size:0.85em; opacity:0.8;'>{row['landkreis']}, {row['bundesland']}</span><br>"
                f"<span style='font-size:0.85em; opacity:0.8;'>{measurementtitles[row['_measurement']]}</span><br>"
                f"<br><span style='font-size:1em'><b>Trend:</b></span>"
                f"<span style='font-size:1.5em'> {trend_str}</span><br>"
                f"<span style='font-size:1em'><b>Letzter Wert:</b></span> "
                f"<span style='font-size:1em'>{last_value}</span><br>"
                f"<span style='font-size:0.85em; opacity:0.8;'>{last_time}</span>"
                f"<br><br><span style='font-size:0.85em; opacity:0.8;'>Punkt anklicken um mehr Informationen zu erhalten!</span>"
            )
            return s
    else:
        def make_string(row):
            trend_str = format_trend_str(row["trend"]["mean"])
            size = row["trend"]["size"]
            s = (
                f"<span style='font-size:1.5em'><b>{row[mode].to_string().strip()}</b></span><br>"
                f"<span style='font-size:0.85em; opacity:0.8;'>Messpunkte: {size}</span><br>"
                f"<span style='font-size:1em'><b>Durchschnittlicher Trend:</b></span>"
                f"<span style='font-size:1.5em'> {trend_str}</span>"
                f"<br><br><span style='font-size:0.85em; opacity:0.8;'>Anklicken um mehr Informationen zu erhalten!</span>"
            )
            return s
    return list(df.apply(lambda x: make_string(x), axis=1))


fieldnames = {
    "airquality": "airquality_score",
    "bikes": "bike_count",
    "hystreet": "pedestrian_count",
    "webcam": "personenzahl",
    "webcam-customvision": "personenzahl",
    "mdm": "vehicleFlow",
    "writeapi": "count",
}
originnames = {
    "airquality": "World Air Quality Index",
    "bikes": "Eco Compteur",
    "hystreet": "hystreet.com",
    "webcam": "öffentliche Webcam (alt)",
    "webcam-customvision": "öffentliche Webcam",
    "mdm": "Mobilitäts Daten Marktplatz (MDM)",
    "writeapi": "Gemeldete Ereignisse",
}
measurementtitles = {
    "airquality": "Luftqualitäts-Index",
    "bikes": "Fahrräder",
    "hystreet": "Fußgänger (Laserscanner)",
    "webcam": "Fußgänger auf Webcams (alt)",
    "webcam-customvision": "Fußgänger auf Webcams",
    "mdm": "Fahrzeuge",
    "writeapi": "Ereignisse",
}
timeformats = {
    "airquality": "%d.%m.%Y %H:%M",
    "bikes": "%d.%m.%Y",
    "hystreet": "%d.%m.%Y",
    "webcam": "%d.%m.%Y %H:%M",
    "webcam-customvision": "%d.%m.%Y %H:%M",
    "mdm": "%d.%m.%Y %H:%M",
    "writeapi": "%d.%m.%Y %H:%M",
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
    zoom_y = -1.446 * log(width_y) + 7.2753
    zoom_x = -1.415 * log(width_x) + 8.7068
    return min(round(zoom_y, 2), round(zoom_x, 2)), centerlat, centerlon


def apply_model_fit(df, model, trend_window):
    """
    Add a column "fit" to a DataFrame with a "_time" column
    For this, apply linear regression with model parameters a (slope) and
    b (offset) to the unixtimestamp value of "_time". Do this only
    for values inside the trend_window
    """
    df["fit"] = nan
    try:
        a, b = model
    except TypeError:
        return df
    day0 = max(df["_time"]) - timedelta(days=trend_window - 1)
    df.loc[df["_time"] >= day0, "fit"] = df[df["_time"] >= day0].apply(lambda x: a * int(x["_time"].timestamp()) + b,
                                                                       axis=1)
    return df


def filter_by_consent(df):
    """
    This is for the webcams only
    Check whether we have obtained consent from the
    webcam owner and keep only entries where this is the case
    """
    webcam_list_url = "https://raw.githubusercontent.com/socialdistancingdashboard/SDD-Webcam-CustomVision/master/webcam_list_2.json"
    try:
        webcams_df = pd.read_json(webcam_list_url)
    except ValueError:
        logging.warning("Cannot read webcam JSON")
        return pd.DataFrame()  # empty dataframe
    webcams_df["ID_Name"] = webcams_df.apply(lambda x: str(x["ID"]) + "_" + x["Name"], 1)
    df["ID_Name"] = df.apply(lambda x: x["_id"].split("_")[0] + "_" + x["name"], 1)
    webcams_df = webcams_df[["ID_Name", "consent"]]
    df = df.merge(webcams_df, on="ID_Name", how="left")
    df = df[df["consent"] == True]
    df = df.drop(["consent", "ID_Name"], errors="ignore", axis=1).reset_index(drop=True)
    return df


local_tz = pytz.timezone('Europe/Berlin')


def utc_to_local(utc_dt):
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)
