#!/bin/bash

#pull any updates before starting the serve
sleep 1m
branch="dashboard-example"
home=/home/$USER/Fiber-optic-project
cd $home
git pull origin $branch
source env/bin/activate

python admin_api.py  &
python app.py
