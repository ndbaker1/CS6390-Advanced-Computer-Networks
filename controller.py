import os
from time import sleep


class Controller:
    def __init__(self):
        self.node_indexes = {}

    def run(self):
        i = 0
        while i < 120:
            for message_file in [x for x in os.listdir('.') if 'from' in x]:
                with open(message_file) as mf:
                    lines = mf.readlines()

                    if message_file in self.node_indexes:
                        last_read_index = self.node_indexes[message_file]
                    else:
                        last_read_index = 0

                    new_lines = lines[last_read_index:]
                    self.node_indexes[message_file] = len(lines)

                    for line in new_lines:
                        fields = line.split(' ')
                        destination_node = fields[0]

                        if destination_node == '*':
                            sender = fields[1]
                            for listener in [x for x in os.listdir('.') if 'to' in x and x != 'to%s' % sender]:
                                with open(listener, 'a') as dest_file:
                                    dest_file.write(line)
                        else:
                            with open('to%s' % destination_node, 'a') as dest_file:
                                dest_file.write(line)
            sleep(1)
            i += 1


if __name__ == "__main__":
    Controller().run()

    print('controller finished.')
