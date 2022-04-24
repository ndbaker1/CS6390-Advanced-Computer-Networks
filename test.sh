#!/bin/sh
echo "0 UP 0 1
0 UP 1 0
0 UP 1 2
0 UP 2 1
0 UP 2 3
0 UP 3 2" > topology.txt

./node.py 0 2 "sending from 0 to 2" 20 &
./node.py 1 1 &
./node.py 2 2 &
./node.py 3 3 &
./controller.py &
