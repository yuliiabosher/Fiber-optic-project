#!/bin/bash

#pull any updates before starting the server
git -C  /home/$1/Fiber-optic-project/ pull origin $branch

#export the flask app path with the user passed as an arg
#otherwise due to systemd running the user would be root and the path would not be found
export FLASK_APP=/home/$1/rtsp_endpoint/app.py
sudo flask run --host=0.0.0.0 --port=443
