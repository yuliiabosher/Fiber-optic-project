#!/bin/bash

#pull any updates before starting the serve
sleep 1m
branch="dashboard-example"
home=/home/$USER/Fiber-optic-project
cd $home
git pull origin $branch
source env/bin/activate

2>/dev/null 1>python admin_api.py 2 &
python app.py
