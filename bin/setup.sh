#SET-UP ZeroTier for ftp
curl -s 'https://raw.githubusercontent.com/zerotier/ZeroTierOne/main/doc/contact%40zerotier.com.gpg' | gpg --import && \  
if z=$(curl -s 'https://install.zerotier.com/' | gpg); then echo "$z" | sudo bash; fi

#Join Zerotier network
sudo zerotier-cli join 856127940c728cdd

#Fail if any command executes with a non-zero status
set -e

#install pip and python3.11
sudo apt install python3.11*
sudo apt install python3-pip

#install pyftpdlib for running an ftpserver when needed
python3.11 -m pip install pyftpdlib

#install dependency requirements
python3.11 -m pip install -r $HOME/Fiber-optic-project/requirements.txt

#copy service so that the system can see it
sudo cp /etc/systemd/system /etc/systemd/system

#Change filepath in dashboard.service to point directly at  the user who installs it , which should be the same user that runs it
sed -i 's/$user/'$USER/ /etc/systemd/dashboard.service

#reload systemd to see the copied file
sudo systemctl daemon-reload
 
 #enable and start the service
sudo systemctl enable dashboard.service
sudo systemctl start dashboard.service