#!/bin/bash

#pull any updates before starting the server
branch="dashboard-example"
home=/home/$USER/Fiber-optic-project
git -C  $home pull origin $branch
source $home/env/bin/activate
python $home/app.py
