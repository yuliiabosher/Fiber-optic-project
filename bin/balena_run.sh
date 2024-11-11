#!/bin/bash

#pull any updates before starting the server
branch="dashboard-example"
git -C  /var/www/html/pull origin $branch

#mount drive with data files on it
mount /dev/sda1 /var/www/html/files/data

#Start webserver
python3.11 
