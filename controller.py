#!/usr/bin/env python3
import os
from time import sleep
from typing import Set

'''
The Controller emulates the topology of a network of wireless nodes with unidirectional links
'''


class Controller:
    def __init__(self):
        # last read line index from each node output file (fromXXX)
        self.indexes: dict[int, int] = dict()
        # each node stores a set of neighbors
        self.topology: dict[int, Set[int]] = dict()
        # a changset keyed by a int timer, which enables the delayed changes in topology
        self.topology_changes: dict[int, Set[(int, int, int)]] = dict()
        # load topology
        self.load_topology()
        # perform a timeout to allow the nodes to complete setup
        sleep(1)

    ''' parse the topology file '''

    def load_topology(self):
        with open('topology.txt') as top:
            # filter out empty lines to avoid parsing exceptions
            for line in filter(lambda e: len(e) > 0, top.readlines()):
                # read the first 4 fields from each line separated by spaces
                delay, state, source, destination = line.split(' ')
                # convernt numeric strings into integers
                delay = int(delay)
                source = int(source)
                destination = int(destination)

                # create a change set or use the currently stored value for every timestamp encountered
                change_set = self.topology_changes.get(delay, set())
                change_set.add((state, source, destination))

                # update the map storing changes by timestamp
                self.topology_changes[delay] = change_set

    ''' process updates using the topology changeset '''

    def update_topology(self, clock):
        # place each update into the current topology map
        for state, source, destination in self.topology_changes.get(clock, []):
            # fetch the original set or create a new one
            neighbor_set = self.topology.get(source, set())

            # UP or DOWN operations to adjust links
            if state == 'UP':
                neighbor_set.add(destination)
            elif state == 'DOWN':
                neighbor_set.discard(destination)

            # update the key with the new neighbor set
            self.topology[source] = neighbor_set

    ''' run the simulation for 120 seconds '''

    def run(self):
        i = 0
        while i < 120:
            # check if there is a topology update for the controller
            self.update_topology(i)
            # processes any messages for which a message from a node should be passed to its neighbors
            for node, neighbors in self.topology.items():
                with open('from%d' % node) as mf:
                    lines = mf.read().splitlines()
                    # start a new index 0 or start from the last index for the current node
                    last_index = 0 if node not in self.indexes else self.indexes[node]
                    # update the most recent index of the node to the length of the inbox file
                    self.indexes[node] = len(lines)
                    # process the newest messages from the node and broadcast them to the neighboring nodes
                    for line in lines[last_index:]:
                        for neighbor in neighbors:
                            with open('to%d' % neighbor, 'a') as dest_file:
                                dest_file.write(line + '\n')
            # sleep the clock
            sleep(1)
            i += 1


if __name__ == "__main__":
    Controller().run()

    print('controller finished.')
