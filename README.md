# Wsl on windows
install wsl
run "wsl"


# Get Token on github
Your profile picture in on the top right position of the project page
github profile picture -> Settings -> Developper Settings -> Personnal Access Token -> Token (classic) -> Generate New Token (Classic)
Note : WSL
project

# Run on a Linux system or wsl
Copy past token from gihub
```
read -s TOKEN
```

Clone the project
```
git clone https://token:$TOKEN@github.com/alsaghir-zin/starcraft.git
```

Pull the project
```
{
cd ./starcraft ;
git pull ;
}
```
Run the project
```
{
git pull ;
./sc.py ;
}
``` 
Install missing packages , could be via pip or package manager 
```
# You may to install some packages
# Here on ubuntu

# apt list |grep python | grep term
# apt list --installed | grep term
# python3 -m pip install --upgrade termcolor
{
sudo apt-get update
sudo apt-get install python3-termcolor
sudo apt-get install make
}
```

# Trick 
if terminal is garbled :
```
stty sane  ^j
```

or 
```
reset
```
