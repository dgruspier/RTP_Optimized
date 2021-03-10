###############################################################################
# sender.py
# Names: Daniel Gruspier, Kenneth Chan
# BU IDs: U88626811, U44559580
###############################################################################

import sys
import socket
#import random
#import time

from util import *
PKT_SIZE = 1472	# Bytes
WAIT_TIME = 0.5 # seconds
LOAD_LEN = 43 # Characters
BUFFER_LEN = 1400 # Bytes

def sender(receiver_ip, receiver_port, window_size):
    """TODO: Open socket and send message from sys.stdin"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   
    # Establish .type values
    START = 0
    END = 1
    DATA = 2
    ACK = 3

    # START message------------------------------------------------
    start_seq = 493829
    pkt_header = PacketHeader(type=START,seq_num = start_seq,length=0)
    pkt_header.checksum = compute_checksum(pkt_header / '')
    pkt = pkt_header / ''
    start_ack = ''
    start_ack_header = PacketHeader(start_ack)
    s.sendto(str(pkt), (receiver_ip, receiver_port))
    ack_checksum = 1
    computed_checksum = 2
    while True:				# Keep sending until we get an ACK
	if start_ack_header.type == ACK and start_ack_header.seq_num == start_seq and computed_checksum == ack_checksum:
		break
        s.settimeout(WAIT_TIME)		# Set 500ms timeout timer
    	try:
		start_ack , address = s.recvfrom(PKT_SIZE)	# Try to receive ACK on the socket
                start_ack_header = PacketHeader(start_ack[:16])
		ack_checksum = start_ack_header.checksum
		start_ack_header.checksum = 0
		computed_checksum = compute_checksum(start_ack_header / '')
	except:				# If 500ms pass and there is no ACK...
                s.sendto(str(pkt), (receiver_ip, receiver_port))	# Resend START

    # DATA message--------------------------------------------------
    
    next_seq = 0		# First seq_num in the window
    all_pkts = []		# Store all pkts in memory in case retransmission is needed
    all_seqs = []		# For tracking which packets have already been created
    all_ack_seqs = []		# Tracks which ACKs have been received
    onoff = True		# Are we still processing?
    keep_reading = True		# Are we still reading data from stdin?
    ack_checksum = 1
    computed_checksum = 2
    while onoff:
	for i in range(next_seq,next_seq + window_size):
                if not i in all_seqs and keep_reading:
			final_seq = i - 1 	# Updates which seq_num is final; locks out when done reading
			message = sys.stdin.read(BUFFER_LEN)
			if message == '':	# No more data condition
				keep_reading = False		# Never execute this for loop again; final_seq locked
			else:
				pkt_header = PacketHeader(type=DATA,seq_num=i,length=len(message))   # Make pkt
				pkt_header.checksum = compute_checksum(pkt_header / message)
				pkt = pkt_header / message
				all_pkts.append(pkt)
				all_seqs.append(pkt_header.seq_num)
	for p in all_seqs:		# Look at which seq_nums have been sent...
		if not p in all_ack_seqs:	# For those which have not been ACKed (i.e. failed to send)...
			s.sendto(str(all_pkts[all_seqs.index(p)]), (receiver_ip, receiver_port))	# Retransmit
	window = range(next_seq,next_seq + window_size)		# Establish current transmission window
	for h in window:				# Cycle through seq_nums in window
		s.settimeout(WAIT_TIME)			# Set timer
                if h not in all_ack_seqs:	# If seq_num has not been ACKed and is not out of range...
			try:					# Try to get its ACK
				ack_pkt , address = s.recvfrom(PKT_SIZE)	
				ack_header = PacketHeader(ack_pkt[:16])
				ack_checksum = ack_header.checksum
				ack_header.checksum = 0
				computed_checksum = compute_checksum(ack_header / '')
				# If not already ACKed...
				if not ack_header.seq_num in all_ack_seqs\
				   and computed_checksum == ack_checksum:
					all_ack_seqs.append(ack_header.seq_num)	# Add it to the list of recv'd ACKs
				if ack_header.type == ACK and ack_header.seq_num == next_seq \
		   	   	   and not ack_header.seq_num > (next_seq + window_size)\
				   and computed_checksum == ack_checksum:	# If this is a good ACK...
					next_seq += 1				# Increment the window
				for m in range(len(all_ack_seqs)):
					if next_seq in all_ack_seqs:     # Try to increment the window using previously recv'd ACKs
						all_ack_seqs.remove(next_seq)
						if next_seq in all_seqs:
							del all_pkts[all_seqs.index(next_seq)]
							all_seqs.remove(next_seq)
						next_seq += 1
			except:
				pass
	for i in all_ack_seqs:
		if i < next_seq:		# Wipe out-of-window ACKs as they are unneeded
			all_ack_seqs.remove(i)
			if i in all_seqs:
				del all_pkts[all_seqs.index(i)]
				all_seqs.remove(i)
	if not keep_reading and next_seq > final_seq:		# "Finished transmitting data" condition
		onoff = False
			
    # END message-------------------------------------------------------------
 # NOTE: essentially identical to START workflow
    end_seq = 99999
    end_pkt_header = PacketHeader(type=END, seq_num=end_seq, length=0)
    end_pkt_header.checksum = compute_checksum(end_pkt_header / '')
    end_pkt = end_pkt_header / ''
    end_ack = ''
    end_ack_header = PacketHeader(end_ack)
    s.sendto(str(end_pkt), (receiver_ip, receiver_port))
    ack_checksum = 1
    computed_checksum = 2
    while True:
    	if end_ack_header.type==ACK and end_ack_header.seq_num==end_seq and computed_checksum == ack_checksum:
		break
	s.settimeout(WAIT_TIME)
	try:
		end_ack, address = s.recvfrom(PKT_SIZE)
		end_ack_header = PacketHeader(end_ack[:16])
		ack_checksum = end_ack_header.checksum
		end_ack_header.checksum = 0
		computed_checksum = compute_checksum(end_ack_header / '')
	except:
		s.sendto(str(end_pkt), (receiver_ip, receiver_port))                
    s.close()

def main():
    """Parse command-line arguments and call sender function """
    if len(sys.argv) != 4:
        sys.exit("Usage: python sender.py [Receiver IP] [Receiver Port] [Window Size] < [message]")
    receiver_ip = sys.argv[1]
    receiver_port = int(sys.argv[2])
    window_size = int(sys.argv[3])
    sender(receiver_ip, receiver_port, window_size)

if __name__ == "__main__":
    main()
