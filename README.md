# Wsl on windows
install wsl
run "wsl"


# Get Token on github
Your profile picture in on the top right position of the project page
github profile picture -> Settings -> Developper Settings -> Personnal Access Token -> Token (classic) -> Generate New Token (Classic)
- Note : WSL
- repo
- project 

# Run on a Linux system or wsl
Copy past token from gihub
```
read -p "Paste the TOKEN and press enter : " -s TOKEN
```

Clone the project
```
git clone https://token:$TOKEN@github.com/alsaghir-zin/starcraft.git
```

Update the project
```
{
cd starcraft
git remote remove origin
git remote add origin https://token:$TOKEN@github.com/alsaghir-zin/starcraft.git
#git push --set-upstream origin main
git fetch
git branch --set-upstream-to=origin/main main
git config --local user.email "zeinsagher@gmail.com"
git config --local user.name "alsaghir-zin"
git pull
git push
}
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
# See Makefile
# make
git pull ;
./sc.py ;
}
```
Push battle_log.txt
{
# See Makefile
make push
}
 
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
