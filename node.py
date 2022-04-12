import time

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
def OLSR():
  def createTC():
    pass
  def createHELLO():
    pass

  i = 0
  while i < 120:
    with open() as recieved:
      pass
    pass
  pass

if __name__ == "__main__":
  OLSR()
