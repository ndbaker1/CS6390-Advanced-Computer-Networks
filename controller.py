import os
from time import sleep


class Controller:
    def __init__(self):
        self.indexes = {}
        self.topology = {}
        self.topology_changes = {}

        with open('topology.txt') as top:
            for line in filter(lambda e: len(e) > 0, top.readlines()):
                delay, state, source, destination = line.split(' ')
                delay = int(delay)
                source = int(source)
                destination = int(destination)

                change_set = self.topology_changes.get(delay, set())
                change_set.add((state, source, destination))

                self.topology_changes[delay] = change_set

    def update_topology(self, clock):
        for state, source, destination in self.topology_changes.get(clock, []):
            neighbor_set = self.topology.get(source, set())

            if state == 'UP':
                neighbor_set.add(destination)
            elif state == 'DOWN':
                neighbor_set.remove(destination)

            self.topology[source] = neighbor_set

    def run(self):
        i = 0
        while i < 120:
            self.update_topology(i)
            for node, neighbors in self.topology.items():
                with open('from%d' % node) as mf:
                    lines = mf.readlines()

                    last_index = 0 if node not in self.indexes else self.indexes[node]

                    self.indexes[node] = len(lines)

                    for line in lines[last_index:]:
                        fields = line.split(' ')
                        destination_node = fields[0]

                        if destination_node == '*':
                            sender = fields[1]
                            for neighbor in neighbors:
                                with open('to%d' % neighbor, 'a') as dest_file:
                                    dest_file.write(line)
                        else:
                            with open('to%s' % destination_node, 'a') as dest_file:
                                dest_file.write(line)
            sleep(1)
            i += 1


if __name__ == "__main__":
    Controller().run()

    print('controller finished.')
