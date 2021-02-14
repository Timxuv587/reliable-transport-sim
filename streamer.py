# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
# import struct
import time
import concurrent.futures

class Streamer:
    def __init__(self, dst_ip, dst_port,
                 #None type
                 src_ip=INADDR_ANY, src_port=0, recv_buffer={}):

        """Default values listen on all network interfaces, chooses a random source port,
           and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.recv_buffer = recv_buffer
        self.seq = []
        self.current_recv_seq = 0
        self.current_send_seq = 0
        self.closed = False
        self.src_ip = src_ip
        self.src_port = src_port
        self.ack = False
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(self.listener)



    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!

        # for now I'm just sending the raw application-level data in one UDP payload
        length = len(data_bytes)
        index = 0
        #Create a header with current sequence
        #header name and header value is seperated by ":"
        #All headers and the true data content is seperate by ";"
        header = "DataSeq:" + str(self.current_send_seq) + ";"
        #Get the header length in order to accomodate packet size
        l = len(header.encode())
        while length - index > 1472 - len(header.encode()):
            data = data_bytes[index:index+1472-l]
            #Decode data to string, combine with header, and encode to bytes
            new_data = (header+data.decode()).encode()
            self.socket.sendto(new_data, (self.dst_ip, self.dst_port))
            index += 1472 - l
            #Update seq num and header
            self.current_send_seq += 1
            header = "DataSeq:" + str(self.current_send_seq) + ";"
            l = len(header.encode())
        header = "DataSeq:" + str(self.current_send_seq) + ";"
        new_data = (header + data_bytes[index:length].decode()).encode()
        self.current_send_seq += 1
        self.socket.sendto(new_data, (self.dst_ip, self.dst_port))
        while not self.ack:
            time.sleep(0.01)


    def listener(self):
        while not self.closed:  # a later hint will explain self.closed
            try:
                # self.ack = False
                data, addr = self.socket.recvfrom()
                # store the data in the receive buffer
                data_str = data.decode('utf-8')
                if data_str == "ACK":
                    self.ack = True
                    # break
                else:
                    seq_number = int(data_str.split(";")[0].split(":")[1])
                    true_data = data_str.split(";")[1].encode()

                    self.recv_buffer[seq_number] = true_data
                    self.seq.append(seq_number)

            except Exception as e:
                print("listener died!")
                print(e)

    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!

        #If data out of order, keep receiving till the packet of current sequence number is received. 
        while(self.current_recv_seq not in self.seq):
            # this sample code just calls the recvfrom method on the LossySocket
            # data, addr = self.socket.recvfrom()

            # #header name and header value is seperated by ":"
            # #All headers and the true data content is seperate by ";"
            # data_str = data.decode('utf-8')
            # seq_number = int(data_str.split(";")[0].split(":")[1])
            # true_data = data_str.split(";")[1].encode()
            #
            # #Store data to buffer base on sequence number
            # self.recv_buffer[seq_number] = true_data
            # self.seq.append(seq_number)

        #Return data that match current seq number
            # if self.current_recv_seq in self.seq:
            continue
        header = "ACK"
        self.current_recv_seq += 1
        self.socket.sendto(header.encode(), (self.src_ip, self.src_port))
        return self.recv_buffer[self.current_recv_seq-1]


    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        self.closed = True
        self.socket.stoprecv()
