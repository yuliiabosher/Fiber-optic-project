user=$USER
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
requirements=$HOME/Fiber-optic-project/requirements.txt
sudo python3.11 -m pip install -r $requirements

#Change filepath in dashboard.service to point directly at  the user who installs it , which should be the same user that runs it
sed -i 's/$user/'$user/ /$HOME/Fiber-optic-project/bin/dashboard.service
sed -i 's/$user/'$user/ /$HOME/Fiber-optic-project/bin/run.sh
sudo chmod +x  /home/$user/Fiber-optic-project/bin/run.sh
#copy service so that the system can see it
sudo cp /home/$user/Fiber-optic-project/bin/dashboard.service /etc/systemd/system
sudo cp /home/$user/Fiber-optic-project/bin/run.sh /

#reload systemd to see the copied file
sudo systemctl daemon-reload
 
#enable and start the service
sudo systemctl enable dashboard.service
sudo systemctl start dashboard.service

#checkout changes to revert back to before the service was changed
#changes not needed anymore as it has been copied
#Plus future automated pulls from git would be prevented if we make changes without commiting them
#so lets just checkout the original files
git -C  $HOME/Fiber-optic-project/ reset .
git -C  $HOME/Fiber-optic-project/ checkout .


