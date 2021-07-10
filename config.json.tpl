{
"influx_url" : "http://ec2-18-196-130-34.eu-central-1.compute.amazonaws.com:9999",
"influx_token" : {{EveryoneCounts/Influx/ReadToken}},
"influx_org" : "ec",
"dash_host" : {{EveryoneCounts/Influx/Host}},
"TRENDWINDOW" : 7,
"DEBUG": false,
"measurements_dashboard": ["webcam-customvision", "writeapi"],
"measurements_widget": ["webcam-customvision", "writeapi"],
"ENABLE_CACHE" : true,
"CLEAR_CACHE_ON_STARTUP" : true,
"SLOW_CACHE_CONFIG": {
  "CACHE_TYPE": "filesystem",
  "CACHE_DIR": "cache",
  "CACHE_THRESHOLD": 100,
  "CACHE_DEFAULT_TIMEOUT": 1800
  },
"FAST_CACHE_CONFIG": {
  "CACHE_TYPE": "filesystem",
  "CACHE_DIR": "cache2",
  "CACHE_THRESHOLD": 200,
  "CACHE_DEFAULT_TIMEOUT": 120
  },
"AUTO_REFRESH_SLOW_CACHE_ENABLE": true,
"LOG_LEVEL": "DEBUG",
"BASE_URL": "https://everyonecounts.de"
}
