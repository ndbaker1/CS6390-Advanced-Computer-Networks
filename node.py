import time
from sys import argv

'''
initialize variables
open fromX.txt for appending, toX.txt for reading,
and Xreceived for appending.
i = 0
while (i < 120)
read toX.txt
process any new received messages (i.e. DATA, HELLO, TC)
if it is time to send the data string
if there is a routing table entry for the destination
send the data message
if i is a multiple of 5 send a hello message
if i is a multiple of 10 send a TC message
remove old entries of the neighbor table if necessary
remove old entries from the TC table if necessary
recalculate the routing table if necessary
i = i + 1;
sleep for 1 second.
end while
close files
end program
'''
class OLSR:
  def __init__(self, node_id: int):
    self.node_id = node_id

  def send_tc(self):
    pass
  def send_hello(self):
    pass
  def send_data(dest: int, message: str):
    pass

  def run(self, message: (int, str, int) = (-1, "", -1)):
    destination_id, message, delay = message
    i = 0
    while i < 120:
      if i == delay:
        self.send_data(destination_id, message)
      if i % 5 == 0:
        self.send_hello()
      if i % 10 == 0:
        self.send_tc()

      i += 1

if __name__ == "__main__":
  source_id, destination_id = map(int, argv[1:3])
  if source_id == destination_id:
    OLSR(source_id).run()
  else:
    message, delay = argv[3], int(argv[4])
    OLSR(source_id).run((destination_id, message, delay))

