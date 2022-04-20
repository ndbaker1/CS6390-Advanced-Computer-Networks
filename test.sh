#!/bin/sh
echo "0 UP 0 1
0 UP 1 0
0 UP 1 2
0 UP 2 1
0 UP 2 3
0 UP 3 2" > topology.txt

python node.py 0 2 "sending from 0 to 2" 20 &
python node.py 1 1 &
python node.py 2 2 &
python node.py 3 3 &
python controller.py &