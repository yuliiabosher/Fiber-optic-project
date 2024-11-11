#!/bin/bash

#pull any updates before starting the server
branch="dashboard-example"
git -C  /var/www/html/ pull switch $branch
git -C  /var/www/html/ pull origin $branch

#mount drive with data files on it
mkdir files/data
mount /dev/sda /var/www/html/files/data

#Start webserver
python3.11 app.py
