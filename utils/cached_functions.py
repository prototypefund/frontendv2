"""
wrappers around the functions from queries.py and map_traces-py to make
them cache-able.

Note: using cache.cached instead of cache.memoize
yields "RuntimeError: Working outside of request context."
"""

import logging
import json
from utils import queries, map_traces
from app import slow_cache, fast_cache

with open("config.json", "r") as f:
    CONFIG = json.load(f)

DISABLE_CACHE = not CONFIG["ENABLE_CACHE"]  # set to true to disable caching
TRENDWINDOW = CONFIG["TRENDWINDOW"]
MEASUREMENTS_DASHBOARD = CONFIG["measurements_dashboard"]

query_api = queries.get_query_api_from_config(CONFIG)


# FUNCTIONS USING THE SLOW CACHE
# ------------------------------

@slow_cache.memoize(unless=DISABLE_CACHE)
def get_map_data(measurements=MEASUREMENTS_DASHBOARD):
    logging.debug("SLOW CACHE MISS")
    return queries.get_map_data(
        query_api=query_api,
        measurements=measurements,
        trend_window=TRENDWINDOW)


@slow_cache.memoize(unless=DISABLE_CACHE)
def get_map_traces(measurements=MEASUREMENTS_DASHBOARD):
    logging.debug("SLOW CACHE MISS")
    map_data = get_map_data(measurements)
    return map_traces.get_map_traces(map_data, measurements)


# FUNCTIONS USING THE FAST CACHE
# ------------------------------

@fast_cache.memoize(unless=DISABLE_CACHE)
def load_timeseries(_id):
    logging.debug(f"FAST CACHE MISS ({_id})")
    return queries.load_timeseries(query_api, _id)


@fast_cache.memoize(unless=DISABLE_CACHE)
def load_last_datapoint(c_id):
    logging.debug(f"FAST CACHE MISS ({c_id})")
    return queries.load_last_datapoint(query_api, c_id)
