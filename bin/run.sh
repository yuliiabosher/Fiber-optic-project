#!/bin/bash

#pull any updates before starting the server
branch="dashboard-example"
git -C  /home/$user/Fiber-optic-project/ pull origin $branch

#docker build and run the dashboard, mounting a media driver/folder which holds the data files
#expose port 443
sudo docker build --no-cache -t dashboard . 
sudo docker run -v /media/$user/$usb/data:/var/www/html/files/data:rshared -it -p 443:443 dashboard

