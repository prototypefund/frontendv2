{
"influx_url" : "http://ec2-18-196-130-34.eu-central-1.compute.amazonaws.com:9999",
"influx_token" : {{EveryoneCounts/Influx/ReadToken}},
"influx_org" : "ec",
"dash_host" : {{EveryoneCounts/Influx/Host}},
"TRENDWINDOW" : 7,
"DEBUG": false,
"measurements_dashboard": ["hystreet", "webcam-customvision", "bikes"],
"measurements_widget": ["hystreet", "webcam-customvision", "bikes", "writeapi"],
"ENABLE_CACHE" : true,
"CLEAR_CACHE_ON_STARTUP" : true,
"CACHE_CONFIG": {
  "CACHE_TYPE": "filesystem",
  "CACHE_DIR": "cache",
  "CACHE_THRESHOLD": 500,
  "CACHE_DEFAULT_TIMEOUT": 1800
  },
"LOG_LEVEL": "DEBUG",
"BASE_URL": "https://everyonecounts.de"
}
