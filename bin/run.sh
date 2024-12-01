#!/bin/bash

#pull any updates before starting the server
sleep 5m
branch="dashboard-example"
home=/home/$USER/Fiber-optic-project
git -C  $home pull origin $branch
source $home/env/bin/activate

2>/dev/null 1>python admin_api.py 2 &
python $home/app.py
