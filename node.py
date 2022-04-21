from time import sleep
from sys import argv
from math import inf
from pathlib import Path
from typing import Set, List
from enum import Enum
from dataclasses import dataclass, field

'''

Messages in this simulation are space-delimited strings,
and contain section headings accompanied by (sometimes) variable length content.

There are three types of messages which follow the structures below:

    TC      ==> * <fromnbr> TC <srcnode> <seqno> MS <msnode> ... <msnode>

    HELLO   ==> * <node> HELLO UNIDIR <neighbor> ... <neighbor> BIDIR <neighbor> ... <neighbor> MPR <neighbor> ... <neighbor>

    DATA    ==> <nxthop> <fromnbr> DATA <srcnode> <dstnode> <string>


!!Notes
    - the '*' indicates a flooded message, which means every recieving node counts as a next-hop.
    - DATA messages cannot be flooded.
    -
'''


class NodeStatus(Enum):
    # aka. unidirectional link
    NOT_SYM = 0
    # aka. bidirectional link
    SYM = 1


''' Topology Control Advertisement '''


@dataclass
class TCAdvertisement:
    # sequence number of message
    # used to ignore old messages and recognize new updates to the network
    sequence: int = 0
    # TTL counter for the node this advertisement belongs to
    timer: int = 30
    # list of nodes who have chosen this node as an MPR
    # shows which nodes are reachable from this node as a last-hop
    mpr_selectors: Set[int] = field(default_factory=set)


''' Neighboring nodes and accompanying metadata '''


@dataclass
class Neighbor:
    # id of the neighbor
    node_id: int
    # unidirectional or bidirectional status of the link
    status: 'NodeStatus' = NodeStatus.NOT_SYM
    # TTL counter for this neighbor's entry
    timer: int = 15
    # is this neighbor an MPR for owning node
    is_mpr: bool = False
    # is this neighbor choosing this owning node as an MPR
    is_mpr_selector: bool = False
    # set of bidirectional links from this neighbor. (essentially the 2-hop neighborhood from this owning node)
    neighbor_set: Set[int] = field(default_factory=set)


''' Parse topology control messages and return the data as a tuple in the form (sender, source, sequence, ms_list) '''


def parse_tc(tc_message: str):
    _, sender_id, _, source_id, seq_num, _, *ms_list = tc_message.split()

    sender_id = int(sender_id)
    source_id = int(source_id)
    seq_num = int(seq_num)

    ms_list = [int(node) for node in ms_list]

    return sender_id, source_id, seq_num, ms_list


''' Parse hello messages and return the data as a tuple in the form (sender, unidirs, bidirs, mprs) '''


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


''' Sort read messages based on type (HELLO, TC, DATA) '''


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

    ''' LAZY HELPERS FOR NEIGHBOR DATA '''

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
        # break up the message
        split_message = message.split(' ')
        # check if the destination has a routing entry
        destination_id = int(split_message[4])
        # exit the function early if there is no routing table entry
        if destination_id not in self.routing_table:
            return
        # see if the message is a flooded message or needs a new next hop
        if split_message[0] != '*':  # this field is next-hop
            # update the next hop on the forwarded message
            split_message[0] = str(self.routing_table[destination_id])
        # update the <fromnbr> (forwarded from) header on the forwarded message
        split_message[1] = str(self.node_id)
        # write the new message to the file
        with open('from%d' % self.node_id, 'a') as sent_messages:
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

    ''' compute the routing table using the topology control table entries and neighbor data '''

    def compute_routing_table(self):
        # create temporary graph
        graph: dict[int, Set[int]] = dict()

        # copy the one hop bidirectional neighbors into the topology graph
        graph[self.node_id] = set(self.get_bidirectional_neighbors())

        # add nodes to the topology based on their MPR Selectors
        for node_id, node_data in self.tc_table.items():
            graph[node_id] = node_data.mpr_selectors.copy()

        # add any of the missing bidirectional links
        for node in list(graph.keys()):
            for neighbor in graph[node]:
                # avoid aliasing the neighbor data by creating a copy (shallow is suitable since the data type is int)
                mirror = graph.get(neighbor, set()).copy()
                mirror.add(node)
                graph[neighbor] = mirror

        distance = {
            node: 0 if node == self.node_id else inf
            for node in graph.keys()
        }
        previous = {
            node: None
            for node in graph.keys()
        }
        visited = {
            node: False
            for node in graph.keys()
        }

        # perform link state routing with yourself as the source
        queue = [self.node_id]
        while queue:
            # relax any neighbor of a visited node
            # this works as an alternative to taking the minimum cost link, because this is based on number of hops
            current = queue.pop()
            # mark the node as visited
            visited[current] = True
            # relax neighbors and add to the queue if unexplored
            for adjacent in graph[current]:
                if not visited[adjacent]:
                    queue.append(adjacent)
                # use hops as link costs (constant 1)
                if distance[current] + 1 < distance[adjacent]:
                    distance[adjacent] = distance[current] + 1
                    previous[adjacent] = current

        # clear previous routing table entries
        self.routing_table.clear()
        # find the first hop nodes to each node in the network to add to our routing table
        for node, prev in previous.items():
            # skip the entry if there was no path found
            if prev == None:
                continue
            # save our current state
            current = node
            # walk the path backwards until we hit the source
            while current != self.node_id and previous[current] != self.node_id:
                current = previous[current]
                if current == None:  # logging
                    print(self.node_id, previous, graph, self.neighbors)
            # update the routing table,
            # and use the link_id if the previous is the current node
            self.routing_table[node] = current

    ''' handle tc message '''

    def handle_tc_messages(self, tc_messages: list) -> bool:
        # track changes
        topology_changed = False
        # break apart the tc message string
        for tc in tc_messages:
            sender_id, source_id, seq_num, ms_list = parse_tc(tc)
            # do not handle message if it is from self
            if source_id == self.node_id:
                continue
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
                if sender_id in self.get_mpr_selectors():
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
                self.neighbors[best_pick['id']].neighbor_set
            )
            # mark the neighbor as an MPR
            self.neighbors[best_pick['id']].is_mpr = True

        return topology_changed

    ''' handle data messages '''

    def handle_data_messages(self, data_messages: List[str]):
        for data in data_messages:
            # parse the data for next hop info
            message_components = data.split(' ')
            message_next_hop = int(message_components[0])
            # ensure that this node is supposed to be on the route
            if message_next_hop == self.node_id:
                # read the final destination of the packet
                message_destination_id = int(message_components[4])
                # save it if this node is the designated recipient
                if message_destination_id == self.node_id:
                    with open('recieved%d' % self.node_id, 'a') as recieved_messages:
                        recieved_messages.write(data + '\n')
                # or forward the message to the next hop node on the path to the destination
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

            def filter_next_hop(message: str):
                next_hop = message.split()[0]
                return next_hop == '*' or int(next_hop) == self.node_id

            # return messages which are meant for this node
            return list(filter(filter_next_hop, latest_messages))

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
