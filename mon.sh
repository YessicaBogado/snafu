#!/bin/sh

while true
do
	./gen.py
	inotifywait -r $HOME/functions
done
