all: pull run push
	echo $@

pull:
	git pull

run: pull
	./sc.py
push:
	-git add .
	-git commit -m "NA"
	-git push
