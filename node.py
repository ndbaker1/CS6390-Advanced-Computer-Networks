from time import sleep
from sys import argv
from pathlib import Path


'''
read toX.txt
process any new received messages (i.e. DATA, HELLO, TC)
if it is time to send the data string
if there is a routing table entry for the destination
send the data message
remove old entries of the neighbor table if necessary
remove old entries from the TC table if necessary
recalculate the routing table if necessary
'''

''' parse topology control messages and return the data as a tuple in the form (sender, source, sequence, ms_list) '''


def parse_tc(tc_message: str):
    _, sender_id, _, source_id, seq_num, _, *ms_list = tc_message.split(' ')

    sender_id = int(sender_id)
    source_id = int(source_id)
    seq_num = int(seq_num)
    ms_list = [int(node) for node in ms_list]

    return sender_id, source_id, seq_num, ms_list


''' parse hello messages and return the data as a tuple in the form (sender, unidirs, bidirs, mprs) '''


def parse_hello(hello_message: str):
    _STAR, sender_id, _HELLO, *hello_content = hello_message.split(' ')

    sender_id = int(sender_id)

    UNIDIR_INDEX = hello_content.index('UNIDIR')
    BIDIR_INDEX = hello_content.index('BIDIR')
    MPR_INDEX = hello_content.index('MPR')

    unidir_list = [int(n) for n in hello_content[UNIDIR_INDEX + 1:BIDIR_INDEX]]
    bidir_list = [int(n) for n in hello_content[BIDIR_INDEX + 1:MPR_INDEX]]
    mpr_list = [int(n) for n in hello_content[MPR_INDEX + 1:]]

    return sender_id, unidir_list, bidir_list, mpr_list


class OLSRNode:
    def __init__(self, node_id: int):
        # numeric id of the node
        self.node_id = node_id
        # last read line of the message accepting file
        self.reading_index = 0
        # set of links that are unidirectional
        self.unidirection_links = set()
        # set of links that are bidirectional
        self.bidirection_links = set()
        # set of MPRs chosen by this node
        self.mpr_set = set()
        # set of MS's, for which the indicated node has chosen this node as an MPR
        self.ms_set = set()
        # sequence number of topology control messages go out
        self.tc_seq = 0
        # Topology Control Table created from recieved TC messages
        self.tc_table = dict()
        # Router Table computed from TC Table
        self.routing_table = dict()

        # trigger the creation of files
        Path('to%d' % self.node_id).touch()
        Path('from%d' % self.node_id).touch()
        Path('recieved%d' % self.node_id).touch()

        # give time for other nodes to properly setup
        sleep(1)

    ''' sort read messages based on type (HELLO, TC, DATA) '''

    def sort_messages(self, messages):

        tc_messages = [x for x in messages if x.split(' ')[3] == 'TC'],
        data_message = [x for x in messages if x.split(' ')[3] == 'DATA'],
        hello_messages = [x for x in messages if x.split(' ')[3] == 'HELLO'],

        return hello_messages, tc_messages, data_message

    ''' forward messages by updating their sender node '''

    def forward_message(self, message: str):
        with open('from%d' % self.node_id, 'a') as sent_messages:
          #  update the <fromnbr> on the forwarded message
            split_message = message.split(' ')
            split_message[1] = self.node_id
            updated_message = ' '.join(split_message) + '\n'
            sent_messages.write(updated_message)

    ''' send a tc message into the network '''

    def send_tc(self):
        with open('from%d' % self.node_id, 'a') as sent_messages:
            sent_messages.write(
                '* %d TC %d %d BIDIR %s MS %s\n' % (
                    self.node_id,
                    self.node_id,
                    self.tc_seq,
                    ' '.join(self.ms_set)
                )
            )
        self.tc_seq += 1

    ''' send a hello message into the network '''

    def send_hello(self):
        def grab_name(e): return e[0]
        with open('from%d' % self.node_id, 'a') as sent_messages:
            sent_messages.write(
                '* %d HELLO UNIDIR %s BIDIR %s MPR %s\n' % (
                    self.node_id,
                    ' '.join(map(grab_name, self.unidirection_links)),
                    ' '.join(map(grab_name, self.bidirection_links)),
                    ' '.join(map(grab_name, self.mpr_set)),
                )
            )

    ''' send a data message into the network '''

    def send_data(self, dest_id: int, message: str):
        with open('from%d' % self.node_id, 'a') as sent_messages:
            sent_messages.write(
                '%d %d DATA %d %d %s\n' % (
                    self.compute_next_hop(dest_id),
                    self.node_id,
                    self.node_id,
                    dest_id,
                    message,
                )
            )

    ''' compute the routing table using the topology control table entries '''

    def compute_routing_table(self):
        pass

    ''' handle tc message '''

    def handle_tc_messages(self, tc_messages: list(str)):
        tc_table_change_detected = False
        # break apart the tc message string
        for sender_id, source_id, seq_num, ms_list in map(parse_tc, tc_messages):
            # add an entry into the topology control table if the source has never been seen before,
            # or if the sequence number on the tc message is higher than the last seen
            if source_id not in self.tc_table or self.tc_table[source_id]['seq'] < seq_num:
                self.tc_table[source_id] = {
                    'seq': seq_num,
                    'ms_set': set(ms_list),
                    'timer': 30,
                }
                tc_table_change_detected = True

            self.forward_message(tc)

        # step the timer for the tc_table entries and then remove them if it has been longer than 30 seconds
        for node_id, table_entry in self.tc_table.items():
            table_entry['timer'] -= 10
            if table_entry['timer'] > 0:
                self.tc_table.pop(node_id)
                tc_table_change_detected = True

        if tc_table_change_detected:
            self.compute_routing_table()

    ''' handle hello message '''

    def handle_hello_messages(self, hello_messages: list(str)):
        # break apart the hello message string
        for sender_id, unidir, bidir, mpr in map(parse_hello, hello_messages):
            # step the timer for the tc_table entries and then remove them if it has been longer than 30 seconds
            for node_id, table_entry in self.tc_table.items():
                table_entry['timer'] -= 10
                if table_entry['timer'] > 0:
                    self.tc_table.pop(node_id)

            # handle reception of hello message
            for sender_id, unidir, bidir, mpr in map(parse_hello, hello_msgs):
                self.unidirection_links.add([sender_id, 15])

                for node in unidir:
                    if node == self.node_id:
                        self.bidirection_links.add([sender_id, 15])

                for node in bidir:
                    if node == self.node_id:
                        self.bidirection_links.add([sender_id, 15])

                for node in mpr:
                    if node == self.node_id:
                        self.ms_set.add([sender_id, 15])

            # remove neighbors that have not responsed within the time window
            for neighbor_data in self.unidirection_links.union(self.bidirection_links).union(self.ms_set):
                neighbor_data[1] -= 5
                if neighbor_data[1] < 0:
                    self.unidirection_links.discard(neighbor_data)
                    self.bidirection_links.discard(neighbor_data)
                    self.ms_set.discard(neighbor_data)

    ''' process incoming messages'''

    def process_incoming(self):
        with open('to%d' % self.node_id) as incoming_messages:
            lines = incoming_messages.readlines()
            # fetch the last part of the messages file
            new_msgs = lines[self.reading_index:]
            # update the current reading index
            self.reading_index = len(lines)
            # sort the messages according to type
            hello_msgs, tc_msgs, data_msgs = self.sort_messages(new_msgs)

            # handle reception of data message
            for data in data_msgs:
                if int(data.split(' ')[4]) == self.node_id:
                    with('recieved%d' % self.node_id) as recieved_messages:
                        recieved_messages.write(data)
                else:
                    self.forward_message(data)

            # handle reception of tc message
            # handle reception of hello message
            self.handle_hello(hello_msgs)

    ''' run the simluation for 120 seconds '''

    def run(self, message: (int, str, int) = (-1, "", -1)):
        # deconstruct data that the node will send
        destination_id, message_str, delay = message
        # run for 120 seconds
        i = 1
        while i <= 120:
            # process incoming message contents
            self.process_incoming()
            # check that it is time to send message or delay the signal
            if i == delay:
                if destination_id in self.routing_table:
                    self.send_data(
                        self.routing_table[destination_id], message_str)
                else:
                    delay += 30
            # send hello message
            if i % 5 == 0:
                self.send_hello()
            # send the topology control message
            if i % 10 == 0 and len(self.ms_set) > 0:
                self.send_tc()

            # step the clock
            i += 1
            sleep(1)


if __name__ == "__main__":
    source_id, destination_id = map(int, argv[1:3])
    olsr_node = OLSRNode(source_id)
    if source_id == destination_id:
        olsr_node.run()
    else:
        message, delay = argv[3], int(argv[4])
        olsr_node.run((destination_id, message, delay))

    print('node %d finished.' % source_id)
