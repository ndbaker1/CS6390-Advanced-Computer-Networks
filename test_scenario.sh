#!/bin/bash
echo  "0 UP 0 1
0 UP 1 0
0 UP 1 2
0 UP 2 1
0 UP 2 3
0 UP 3 2
0 UP 3 4
0 UP 4 3
0 UP 4 5
0 UP 5 4
0 UP 5 0
0 UP 0 5
50 DOWN 4 5
50 DOWN 5 4" > topology.txt


python node.py 0 4 "A message from 0 to 4"   40   &
python node.py 1 1 &
python node.py 2 2 &
python node.py 3 3 &
python node.py 4 0 "Message from 4 to 0"  80 &
python node.py 5  5  &
python controller.py &