#Fai; if any command executes with a non-zero status
set -e

#SET-UP ZeroTier for ftp
curl -s 'https://raw.githubusercontent.com/zerotier/ZeroTierOne/main/doc/contact%40zerotier.com.gpg' | gpg --import && \  
if z=$(curl -s 'https://install.zerotier.com/' | gpg); then echo "$z" | sudo bash; fi

#Join Zerotier network
sudo zerotier-cli join 856127940c728cdd

#install pip and python3.11
sudo apt install python3.11*
sudo apt install python3-pip

#install pyftpdlib for running an ftpserver when needed
python3.11 -m pip install pyftpdlib

#install dependency requirements
python3.11 -m pip install -r $HOME/dashboard/requirements.txt
