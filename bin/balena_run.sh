#!/bin/bash

#pull any updates before starting the server
git -C  /var/www/html/ switch $main #switch back to a default repo so that we arent carrying redundant files forward
git -C  /var/www/html/ branch $branch #silently fail if branch already exists, not important, no overwrite can happen and no push permissions
git -C  /var/www/html/ switch $branch
git -C  /var/www/html/ pull origin $branch

#mount drive with data files on it
mkdir files/data
mount /dev/sda2 /var/www/html/files/data

#Start webserver
python3.11 app.py
