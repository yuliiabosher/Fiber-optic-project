#!/bin/bash

#pull any updates before starting the server
branch="dashboard-example"
git -C  /home/$user/Fiber-optic-project/ pull origin $branch

export FLASK_APP=/home/$user/Fiber-optic-project/app.py
sudo flask run --host=0.0.0.0 --port=443
