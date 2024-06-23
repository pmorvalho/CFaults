#!/usr/bin/bash
apt-get update
apt-get install sudo
sudo apt-get install -y zip
sudo apt-get install -y python3
sudo apt-get install -y emacs
sudo apt-get install -y g++ gcc flex bison make git curl patch
sudo apt-get install -y gcc-multilib
sudo apt-get install -y sqlite3
sudo apt-get install -y bc
sudo apt install -y python3-pip
sudo pip3 install --break-system-packages python-sat
sudo pip3 install --break-system-packages numpy
sudo pip3 install --break-system-packages pycparser
sudo pip3 install --break-system-packages matplotlib
sudo pip3 install --break-system-packages pandas
# sudo pip3 install --break-system-packages sqlite3
sudo pip3 install --break-system-packages SQLite3-0611
unzip CFaults-fm2024.zip
mv CFaults/* .
rm -rf CFaults
unzip cbmc.zip
cd cbmc
make -C src minisat2-download
make -C src
cd ..
unzip runsolver.zip
unzip mkplot.zip
unzip tcas.zip
unzip C-Pack-IPAs.zip
./CFaults.sh -i examples/fm2024_example.c -o o -nu 3 -e lab02/ex01 -v
