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


class OLSRNode:
    def __init__(self, node_id: int):
        # last read line of the message accepting file
        self.reading_index = 0
        # numeric id of the node
        self.node_id = node_id
        # set of links that are unidirectional
        self.unidirection_links = []
        # set of links that are bidirectional
        self.bidirection_links = []
        # set of MPRs chosen by this node
        self.mpr_set = []
        # set of MS's, for which the indicated node has chosen this node as an MPR
        self.ms_set = []
        # sequence number of topology control messages go out
        self.tc_seq = 0
        # Topology Control Table created from recieved TC messages
        self.tc_table = []
        # Router Table computed from TC Table
        self.routing_table = {}

        # trigger the creation of files
        Path('to%d' % self.node_id).touch()
        Path('from%d' % self.node_id).touch()
        Path('recieved%d' % self.node_id).touch()

        # give time for other nodes to properly setup
        sleep(1)

    ''' sort read messages based on type (HELLO, TC, DATA) '''

    def sort_messages(self, messages):
        return (
            [x for x in messages if x.split(' ')[3] == 'HELLO'],
            [x for x in messages if x.split(' ')[3] == 'TC'],
            [x for x in messages if x.split(' ')[3] == 'DATA'],
        )

    ''' forward messages by updating their sender node '''

    def forward_message(self, message: str):
        with open('from%d' % self.node_id, 'a') as sent_messages:
          #  update the <fromnbr> on the forwarded message
            split_message = message.split(' ')
            split_message[1] = self.node_id
            updated_message = ' '.join(split_message) + '\n'
            sent_messages.write(updated_message)

    ''' computer the next hop for a given destination node '''

    def compute_next_hop(self, dest_id: int) -> int:
        return 5

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
        with open('from%d' % self.node_id, 'a') as sent_messages:
            sent_messages.write(
                '* %d HELLO UNIDIR %s BIDIR %s MPR %s\n' % (
                    self.node_id,
                    ' '.join(self.unidirection_links),
                    ' '.join(self.bidirection_links),
                    ' '.join(self.mpr_set)
                )
            )

    ''' send a data message into the network '''

    def send_data(dest_id: int, message: str):
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

    ''' place data that is designated for this node into the recieved file '''

    def recieve_data(self, data):
        with open('recieved%d' % self.node_id, 'a') as recieved_messages:
            pass

    ''' process incoming messages'''

    def process_incoming(self):
        with open('to%d' % self.node_id) as incoming_messages:
            # fetch the last part of the messages file
            new_msgs = incoming_messages.readlines()[last_index:]
            # update the current reading index
            self.reading_index = len(lines)
            # sort the messages according to type
            hello_msgs, tc_msgs, data_msgs = self.sort_messages(new_msgs)

            for data in data_msgs:
                if int(data.split(' ')[4]) == self.node_id:
                    with('recieved%d' % self.node_id) as recieved_messages:
                        recieved_messages.write(data)
                else:
                    self.forward_message(data)

            for tc in tc_msgs:
                self.forward_message(tc)

            for hello in hello_msgs:
                pass

    ''' run the simluation for 120 seconds '''

    def run(self, message: (int, str, int) = (-1, "", -1)):
        # deconstruct data that the node will send
        destination_id, message, delay = message
        # run for 120 seconds
        i = 1
        while i <= 120:
            # process incoming message contents
            self.process_incoming()
            # check that it is time to send message or delay the signal
            if i == delay:
                if destination_id in self.routing_table:
                    self.send_data(destination_id, message)
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
