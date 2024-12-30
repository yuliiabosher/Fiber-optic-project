#Fail if any command executes with a non-zero status
set -e

user=$USER

#name of usb where data files are stored
usb=6D2B02C137685C07

# Add Docker's official GPG key:
sudo apt-get update -y
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/raspbian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Set up Docker's APT repository:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/raspbian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

#install the latest docker version
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

#Change filepath in dashboard.service to point directly at  the user who installs it , which should be the same user that runs it
sed -i 's/$user/'$user/ /$HOME/Fiber-optic-project/bin/dashboard.service
sed -i 's/$user/'$user/ /$HOME/Fiber-optic-project/bin/run.sh
sed -i 's/$user/'$user/ /$HOME/Fiber-optic-project/Dockerfile
sed -i 's/$usb/'$usb/ /$HOME/Fiber-optic-project/Dockerfile

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

#This script is no longer needed since we moved to balena,but keeping it just in case we need it in the future
