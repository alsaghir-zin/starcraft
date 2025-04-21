all: pull run push
	echo $@

pull:
	git pull

run: pull
	./sc.py

live: pull
	./sc.py -l --status
	
push:
	-git add .
	-git commit -m "NA"
	-git push
