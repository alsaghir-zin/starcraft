all: pull run push
	echo $@

pull:
	git pull

run: pull
	./sc.py

live: pull
	./sc.py -l --status

help: pull
	./sc.py -h
	
push:
	-git add .
	-git commit -m "NA"
	-git push
