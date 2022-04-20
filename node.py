from time import sleep
from sys import argv
from pathlib import Path
from typing import Set, List
from enum import Enum
from dataclasses import dataclass, field

'''
messages in this simulation follow the following structures:

MESSAGE( CONTENT ) = NEXT_HOP | FORWARDED_FROM | CONTENT
DATA_MESSAGE = MESSAGE( "DATA" | SOURCE_NODE |
                       DESTINATION_NODE | STRING_MESSAGE )
'''


class NodeStatus(Enum):
    NOT_SYM = 0
    SYM = 1


''' Topology Control Advertisement '''


@dataclass
class TCAdvertisement:
    sequence: int = 0
    timer: int = 30
    mpr_selectors: Set[int] = field(default_factory=set)


@dataclass
class Neighbor:
    node_id: int
    status: 'NodeStatus' = NodeStatus.NOT_SYM
    timer: int = 15
    is_mpr: bool = False
    is_mpr_selector: bool = False
    neighbor_set: Set[int] = field(default_factory=set)


''' parse topology control messages and return the data as a tuple in the form (sender, source, sequence, ms_list) '''


def parse_tc(tc_message: str):
    _, sender_id, _, source_id, seq_num, _, *ms_list = tc_message.split()

    sender_id = int(sender_id)
    source_id = int(source_id)
    seq_num = int(seq_num)
    ms_list = [int(node) for node in ms_list]

    return sender_id, source_id, seq_num, ms_list


''' parse hello messages and return the data as a tuple in the form (sender, unidirs, bidirs, mprs) '''


def parse_hello(hello_message: str) -> (int, List[int], List[int], List[int]):
    _STAR, sender_id, _HELLO, *hello_content = hello_message.split()

    sender_id = int(sender_id)

    UNIDIR_INDEX = hello_content.index('UNIDIR')
    BIDIR_INDEX = hello_content.index('BIDIR')
    MPR_INDEX = hello_content.index('MPR')

    unidir_list = [int(n) for n in hello_content[UNIDIR_INDEX + 1:BIDIR_INDEX]]
    bidir_list = [int(n) for n in hello_content[BIDIR_INDEX + 1:MPR_INDEX]]
    mpr_list = [int(n) for n in hello_content[MPR_INDEX + 1:]]

    return sender_id, unidir_list, bidir_list, mpr_list


''' sort read messages based on type (HELLO, TC, DATA) '''


def sort_messages(messages: List[str]):
    tc_messages = [x for x in messages if x.split(' ')[2] == 'TC']
    data_message = [x for x in messages if x.split(' ')[2] == 'DATA']
    hello_messages = [x for x in messages if x.split(' ')[2] == 'HELLO']

    return hello_messages, tc_messages, data_message


''' OLSR Node which sends periodic update messages (hello/tc) and can send instances of string data '''


class OLSRNode:
    def __init__(self, node_id: int):
        # numeric id of the node
        self.node_id: int = node_id
        # last read line of the message accepting file
        self.reading_index: int = 0
        # neighbor set
        self.neighbors: dict[int, 'Neighbor'] = dict()
        # sequence number of topology control messages go out
        self.tc_seq: int = 0
        # Topology Control Table created from recieved TC messages
        self.tc_table: dict[int, 'TCAdvertisement'] = dict()
        # Router Table computed from TC Table
        self.routing_table: dict[int, int] = dict()

        # trigger the creation of files
        Path('to%d' % self.node_id).touch()
        Path('from%d' % self.node_id).touch()
        Path('recieved%d' % self.node_id).touch()

        # give time for other nodes to properly setup
        sleep(1)

    def get_unidirectional_neighbors(self) -> List[int]:
        return [x.node_id for x in self.neighbors.values() if x.status == NodeStatus.NOT_SYM]

    def get_bidirectional_neighbors(self) -> List[int]:
        return [x.node_id for x in self.neighbors.values() if x.status == NodeStatus.SYM]

    def get_mprs(self) -> List[int]:
        return [x.node_id for x in self.neighbors.values() if x.is_mpr]

    def get_mpr_selectors(self) -> List[int]:
        return [x.node_id for x in self.neighbors.values() if x.is_mpr_selector]

    ''' gets the set of 2-hop neighbors '''

    def get_two_hop_neighbor_set(self) -> Set[int]:
        two_hop_neighbor_set = set()
        # union all of the neighbor's neighbor sets together
        for neighbor in self.neighbors.values():
            two_hop_neighbor_set = two_hop_neighbor_set.union(
                neighbor.neighbor_set)

        # remove all of the one-hop neighbors from the two-hop neighbor set
        for neighbor_id in self.neighbors.keys():
            two_hop_neighbor_set.discard(neighbor_id)

        return two_hop_neighbor_set

    ''' forward messages by updating their sender node '''

    def forward_message(self, message: str):
        with open('from%d' % self.node_id, 'a') as sent_messages:
            split_message = message.split(' ')
            # update the <fromnbr> on the forwarded message
            split_message[1] = str(self.node_id)
            updated_message = ' '.join(split_message) + '\n'
            sent_messages.write(updated_message)

    ''' send a tc message into the network '''

    def send_tc(self):
        with open('from%d' % self.node_id, 'a') as sent_messages:
            sent_messages.write(
                '* %d TC %d %d MS %s\n' % (
                    self.node_id,
                    self.node_id,
                    self.tc_seq,
                    ' '.join(map(str, self.get_mpr_selectors())),
                )
            )
        self.tc_seq += 1

    ''' send a hello message into the network '''

    def send_hello(self):
        with open('from%d' % self.node_id, 'a') as sent_messages:
            sent_messages.write(
                '* %d HELLO UNIDIR %s BIDIR %s MPR %s\n' % (
                    self.node_id,
                    ' '.join(map(str, self.get_unidirectional_neighbors())),
                    ' '.join(map(str, self.get_bidirectional_neighbors())),
                    ' '.join(map(str, self.get_mprs())),
                )
            )

    ''' send a data message into the network '''

    def send_data(self, dest_id: int, message: str) -> bool:
        # return error if destination is not in the routing table
        if dest_id not in self.routing_table:
            # failed to send message
            return False
        # fetch next hop router from the routing table
        next_hop = self.routing_table[dest_id]
        # place the data message in the outgoing container
        with open('from%d' % self.node_id, 'a') as sent_messages:
            sent_messages.write(
                '%d %d DATA %d %d %s\n' % (
                    next_hop,
                    self.node_id,
                    self.node_id,
                    dest_id,
                    message,
                )
            )
        # successfully sent message
        return True

    ''' compute the routing table using the topology control table entries '''

    def compute_routing_table(self):
        # clear previous routing table entries
        self.routing_table = dict()
        # starting node is self, as the single source path is rooted at the current node
        current_node = self.node_id

        # create temporary graph
        graph = dict()
        for neighbor_id in self.neighbors.keys():
            graph[neighbor_id] = neighbor_id

        for node, reachable in self.tc_table.items():
            pass

    ''' handle tc message '''

    def handle_tc_messages(self, tc_messages: list) -> bool:
        # track changes
        topology_changed = False
        # break apart the tc message string
        for tc in tc_messages:
            sender_id, source_id, seq_num, ms_list = parse_tc(tc)
            # add an entry into the topology control table if the source has never been seen before,
            # or if the sequence number on the tc message is higher than the last seen
            if source_id not in self.tc_table or self.tc_table[source_id].sequence < seq_num:
                # trigger topology change
                topology_changed = True
                self.tc_table[source_id] = TCAdvertisement(
                    sequence=seq_num,
                    mpr_selectors=set(ms_list),
                )
                # if the sender of this message has chosen this node as an MPR,
                # then forward the message
                if sender_id in self.get_mpr_selectors() and source_id != self.node_id:  # is source != self required?
                    self.forward_message(tc)

        return topology_changed

    ''' handle hello message '''

    def handle_hello_messages(self, hello_messages: list) -> bool:
        # track changes
        topology_changed = False
        # break apart the hello message string
        for sender_id, unidir, bidir, mpr in map(parse_hello, hello_messages):
            # insert never before seen entries
            if sender_id not in self.neighbors:
                self.neighbors[sender_id] = Neighbor(sender_id)
                topology_changed = True

            # reset the lifespan timer for this neighbor
            self.neighbors[sender_id].timer = 15

            # detecting a two-way connection
            if self.node_id in unidir or self.node_id in bidir:
                if self.neighbors[sender_id].status != NodeStatus.SYM:
                    topology_changed = True
                self.neighbors[sender_id].status = NodeStatus.SYM

            # detect if node has chosen me as an MPR, so add it to the MS set
            if self.node_id in mpr:
                if self.neighbors[sender_id].is_mpr_selector != True:
                    topology_changed = True
                self.neighbors[sender_id].is_mpr_selector = True

            # update 2-hop neighbors
            connected_neighbors = set(bidir)
            # exclude self in the neighbor set
            connected_neighbors.discard(self.node_id)
            # check whether updating this set will change the topology
            if connected_neighbors != self.neighbors[sender_id].neighbor_set:
                topology_changed = True
            # update the neighbor set
            self.neighbors[sender_id].neighbor_set = connected_neighbors

        # update MPRs for this node
        two_hop_neighbor_set = self.get_two_hop_neighbor_set()
        # run while there are still two-hop neighbors to cover
        # it is certain this will converge, because the 2-hop neighbor set is derived from the 1-hop neighbors
        while len(two_hop_neighbor_set) > 0:
            best_pick = {'id': 0, 'score': 0}
            for neighbor_id, neighbor in self.neighbors.items():
                # compute the number of 2 hops which this neighbor will cover as an MPR
                nodes_covered = len(two_hop_neighbor_set.intersection(
                    neighbor.neighbor_set
                ))
                # update the current best if the score is higher than the previous best
                if best_pick['score'] < nodes_covered:
                    best_pick['id'] = neighbor_id
                    best_pick['score'] = nodes_covered

            # remove the covered elements from the newest selected MPR set
            two_hop_neighbor_set.difference_update(
                self.neighbors[best_pick['id']].neighbor_set)
            # mark the neighbor as an MPR
            self.neighbors[best_pick['id']].is_mpr = True

        return topology_changed

    ''' handle data messages '''

    def handle_data_messages(self, data_messages: List[str]):
        for data in data_messages:
            message_destination_id = int(data.split(' ')[4])
            if message_destination_id == self.node_id:
                with('recieved%d' % self.node_id) as recieved_messages:
                    recieved_messages.write(data)
            else:
                self.forward_message(data)

    ''' read a list of the most recent messages '''

    def read_latest_messages(self) -> List[str]:
        with open('to%d' % self.node_id) as incoming_messages:
            lines = incoming_messages.read().splitlines()
            # fetch the last part of the messages file
            latest_messages = lines[self.reading_index:]
            # update the current reading index
            self.reading_index = len(lines)
            # return messages
            return latest_messages

    ''' run the simluation for 120 seconds '''

    def run(self, message: (int, str, int) = (-1, "", -1)):
        # deconstruct data that the node will send
        destination_id, message_str, delay = message
        # run for 120 seconds
        i = 1
        while i <= 120:
            # process incoming messages
            latest_messages = self.read_latest_messages()
            # sort the messages according to type
            hello_msgs, tc_msgs, data_msgs = sort_messages(latest_messages)
            # handle reception of data message
            self.handle_data_messages(data_msgs)
            # track state changes from handlers
            changes_detected = False
            # handle reception of tc message
            changes_detected |= self.handle_tc_messages(tc_msgs)
            # handle reception of hello message
            changes_detected |= self.handle_hello_messages(hello_msgs)

            # check that it is time to send message or delay the signal
            if i == delay:
                if not self.send_data(destination_id, message_str):
                    delay += 30
            # send hello message
            if i % 5 == 0:
                self.send_hello()
            # send the topology control message
            if i % 10 == 0 and len(self.get_mpr_selectors()) > 0:
                self.send_tc()

            # step the timer for the tc_table entries and then remove them if it has been longer than 30 seconds
            for node_id in list(self.tc_table.keys()):
                self.tc_table[node_id].timer -= 1
                if self.tc_table[node_id].timer < 0:
                    del self.tc_table[node_id]
                    changes_detected = True

            # remove neighbors that have not responsed within the 10 seconds time window
            for neighbor_id in list(self.neighbors.keys()):
                self.neighbors[neighbor_id].timer -= 1
                if self.neighbors[neighbor_id].timer < 0:
                    del self.neighbors[neighbor_id]
                    changes_detected = True

            # recalculate routing table if neccessary
            if changes_detected:
                self.compute_routing_table()

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
