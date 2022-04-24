# OLSR Network Simulation
Programming Project for Graduate studies in CS6390 Advanced Computer Networks

### Academic Info
**Identification:** Nicholas Baker - ndb180002 <br>
**Server:** csgrads1 <br>
**Runtime:** python 3.6 <br>

## Execution
Use __python3__ or higher to run `node.py` and `controller.py`.
> Only tested for python3.6+

```bash
# example scenario.
./node.py 0 2 "sending from 0 to 2" 20 &
./node.py 1 1 &
./node.py 2 2 &
./controller.py &
```

## Node
Files will be created to facilitate input and output links.
These are read by the controller to forward data based on the network topology, imitating a group of wirless nodes using a broadcast medium.

usage:
```bash
./node.py ID DESTINATION [MESSAGE DELAY]
```
| ID | DESTINATION | MESSAGE | DELAY |
|----|-------------|---------|-------|
| node identifier | destination for message (equals ID to ignore message) | optional message | delay for message |


## Controller
takes no input, reads `topology.txt` for link statuses at indicated timestamps (in seconds)

usage:
```bash
./controller.py
```