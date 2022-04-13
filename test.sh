#!/bin/sh
echo "0 UP 0 1
0 UP 1 0
0 UP 0 2
0 UP 2 0
0 UP 1 2
0 UP 2 1" > topology.txt

python node.py 0 0 &
python node.py 1 2 "sending from 1 to 2" 20 &
python node.py 2 2 &
python controller.py &