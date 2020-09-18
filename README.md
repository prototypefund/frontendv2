# EveryoneCounts Frontend 2

New Dash frontend for https://everyonecounts.de. Work in progress.

## Run
The dash webserver is run on an AWC EC2 instance. For setup and deploy scripts see [this repo](https://github.com/socialdistancingdashboard/virushack/tree/master/dash-deploy).

Important: Requires Dash 1.12. There is an issue with how callbacks are handled in Dash 1.13+ which makes it currently incompatible with this code.

## Configuration file
Dashboard and widget functionality can be customized using `config.json`. Also, credentials are stored in this file. It is generated from `config.json.tpl` using [Secrethub](https://secrethub.io):

```
secrethub inject -i config.json.tpl -o config.json --identity-provider=aws
```

The parameters in the config file are:
- `influx_url` : URL of the InfluxDB
- `influx_token` : Token of the InfluxDB. Stored in Secrethub.
- `influx_org` : Organisation of the InlfuxDB
- `dash_host` : Host address for the Dash Webserver (e.g. `localhost`). Stored in Secrethub.
- `TRENDWINDOW` : Number of days to use for trend calculation
- `DEBUG`: Debug mode of the Dash webserver (boolean)
- `measurements_dashboard`: Names of the measurements that are displayed in the dashboard
- `measurements_widget`: Names of the measurements that can be used as widgets and are shown in the widget configurator
- `ENABLE_CACHE` : Enable caching of calls to the InfluxDB (boolean)
- `CLEAR_CACHE_ON_STARTUP` : Clear the cache upon webserver start (boolean)
- `SLOW_CACHE_CONFIG` and `FAST_CACHE_CONFIG`: Configuration for two different caches. The "slow" cache caches data for longer periods of time (e.g. for all dashboard stations data) while the "fast" cache has a shorter timeout (e.g. for widgets which should update more frequently). See the [Flask-Caching](https://flask-caching.readthedocs.io/en/latest/) documentation for details. The most relevant options are:
    - `CACHE_TYPE`: Specifies which type of caching object to use (e.g. `filesystem`)
    - `CACHE_DIR`: Directory to store cache. Used only for FileSystemCache.
    - `CACHE_THRESHOLD`: The maximum number of items the cache will store before it starts deleting some. Used only for SimpleCache and FileSystemCache
    - `CACHE_DEFAULT_TIMEOUT`: The default timeout that is used if no timeout is specified. Unit of time is seconds.
  },
- `LOG_LEVEL`: Logging level, e.g. `DEBUG`,
- `BASE_URL`: Base URL of the webserver, mostly used for the widgets. For example, this can be `http://localhost:8050` in development and `https:/everyonecounts.de` in deployment.


## Widget

Widgets are accesed on `BASE_URL/widget` and require some URL parameters. For ease of use, there is a configuration UI under `BASE_URL/widget/configurator` that generates the correct URLs and helps in determining the station ids. 

Example URLs: 
- `https://everyonecounts.de/widget?widgettype=timeline&station=hystreet$110&show_rolling=0&show_trend=0`
- `https://everyonecounts.de/widget?widgettype=fill&station=hystreet$110&max=5000&show_number=both`

Parameters for all widget types:
- `station` (required, c_id of the station)
- `width` (optional, width of the widget in pixels)

Possible widget types (`widgettype=`) and their parameters:
- `timeline` (shows a timeline chart)
    - `show_trend` (optional, 1 or 0)
    - `show_rolling` (optional, 1 or 0)
- `fill` (shows how filled a station is)
    - `max` (optional)
    - `show_number` (required, one of 'total', 'percentage' or 'both')
    - `trafficlight` (if set to 1, display a traffic light next to the numbers)
    - `t1` and `t2` (required only when trafficlight is set to 1, thresholds for green/yellow and yellow/red boundary)

