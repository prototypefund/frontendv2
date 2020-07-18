# EveryoneCounts Frontend 2

New Dash frontend for https://everyonecounts.de. Work in progress.

## Run
The dash webserver is run on an AWC EC2 instance. For setup and deploy scripts see [this repo](https://github.com/socialdistancingdashboard/virushack/tree/master/dash-deploy).

## Credentials
Credentials are stored in `config.json`. This file is generated from `config.json.tpl` using [Secrethub](https://secrethub.io):

```
secrethub inject -i config.json.tpl -o config.json --identity-provider=aws
```