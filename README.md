# EveryoneCounts Frontend 2

New Dash frontend for https://everyonecounts.de. Work in progress.

## Run
The dash webserver is run on an AWC EC2 instance. For setup and deploy scripts see [this repo](https://github.com/socialdistancingdashboard/virushack/tree/master/dash-deploy).

Important: Requires Dash 1.12. There is an issue with how callbacks are handled in Dash 1.13+ which makes it currently incompatible with this code.

## Credentials
Credentials are stored in `config.json`. This file is generated from `config.json.tpl` using [Secrethub](https://secrethub.io):

```
secrethub inject -i config.json.tpl -o config.json --identity-provider=aws
```

## Widget
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
- `trafficlight` (shows a trafficlight)
    - `t1` and `t2` (required, thresholds for green/yellow and yellow/red boundary)

