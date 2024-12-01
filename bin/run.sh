#!/bin/bash

#pull any updates before starting the server
branch="dashboard-example"
git -C  /home/$user/Fiber-optic-project/ pull origin $branch
source /home/$user/Fiber-optic-project/env/bin/activate
python /home/$user/Fiber-optic-project/app.py
