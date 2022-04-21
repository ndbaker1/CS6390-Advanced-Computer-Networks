#!/bin/bash

echo "0 UP 0 3
0 UP 3 0
0 UP 0 7
0 UP 7 0
0 UP 1 3
0 UP 3 1
0 UP 1 8
0 UP 8 1
0 UP 2 4
0 UP 2 8
0 UP 8 2
0 UP 2 9
0 UP 9 2
0 UP 3 6
0 UP 6 3
0 UP 4 8
0 UP 8 4
0 UP 6 7
0 UP 7 6
0 UP 6 8
0 UP 8 6
0 UP 7 9
0 UP 9 7
30 DOWN 6 8
30 DOWN 8 6
30 DOWN 1 8
30 DOWN 8 1" > topology.txt

python node.py 0 1 "message from 0" 50 &
python node.py 1 1 &
python node.py 2 2 &
python node.py 3 2 "message from 3" 100 &
python node.py 4 4 &
python node.py 6 6 &
python node.py 7 7 &
python node.py 8 8 &
python node.py 9 2 "message from 9" 25 &
python controller.py &