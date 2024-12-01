#!/bin/bash

#pull any updates before starting the server
branch="dashboard-example"
git -C  /home/$USERr/Fiber-optic-project/ pull origin $branch
source /home/$USER/Fiber-optic-project/env/bin/activate
python /home/$USER/Fiber-optic-project/app.py
