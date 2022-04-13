#!/bin/sh

python node.py 0 0 &
python node.py 1 2 "sending from 1 to 2" 20 &
python node.py 2 2 &
python controller.py &