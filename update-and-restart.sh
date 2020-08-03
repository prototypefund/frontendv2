#!/bin/bash
git pull origin master
secrethub inject -i config.json.tpl -o config.json --identity-provider=aws --force
cd cache
rm *
sudo systemctl restart rundashboard.service
