! on windows
install wsl



! on github
github profile picture -> Settings -> Developper Settings -> Personnal Access Token -> Token (classic) -> Generate New Token (Classic)
Note : WSL
project

! on ubuntu or wsl
# Copy past token from gihub

read -s TOKEN

sudo apt-get install python3-termcolor
git clone https://token:$TOKEN@github.com/alsaghir-zin/starcraft.git

cd ./starcraft
git pull
./sc.py

! Trick 
if terminal is garbled :
stty sane  ^j 
