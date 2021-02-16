# do not import anything else from loss_socket besides LossyUDP
from threading import Lock
from threading import Timer
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
# import struct
import time
import concurrent.futures
import hashlib


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
        self.ack_timeout = 0.25
        self.lock = Lock()
        self.send_data = {}
        self.current_ack_seq = 0
        self.ack = False
        self.time = time.time()
        self.lock_send = False
        self.counter = 0
        self.fin = False

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self.executor.submit(self.listener)



    #Packet format:
    #Normal packet
    #HASH;DataSeq:xxxxxxx;TRUE_DATA
    #ACK packet
    #HASH;ACK;DataSeq:xxxxxx



    def send(self, data_bytes: bytes) -> None:
        with self.lock:
            if(self.lock_send == False):
                """Note that data_bytes can be larger than one packet."""
                # Your code goes here!  The code below should be changed!
                self.ack = False
                # for now I'm just sending the raw application-level data in one UDP payload
                length = len(data_bytes)
                index = 0
                #Create a header with current sequence
                #header name and header value is seperated by ":"
                #All headers and the true data content is seperate by ";"
                # seq_counter = self.current_send_seq
                header = ";DataSeq:" + str(self.current_send_seq) + ";"
        
                #Get the header length in order to accomodate packet size
                l = len(header.encode()) + 16
                # send_packet = []
                while length - index > 1472 - len(header.encode()) - 16:
                    data = data_bytes[index:index+1472-l]
                    #Decode data to string, combine with header, and encode to bytes
                    new_data = (header+data.decode()).encode()
                    m = hashlib.md5()
                    m.update(new_data)
                    hash_new_data = m.digest() + new_data
                    # send_packet.append(hash_new_data)
                    self.send_data[self.current_send_seq] = hash_new_data
                    self.socket.sendto(hash_new_data, (self.dst_ip, self.dst_port))
                    index += 1472 - l
                    #Update seq num and header
                    self.current_send_seq += 1
                    header = ";DataSeq:" + str(self.current_send_seq) + ";"
                    l = len(header.encode()) + 16
                header = ";DataSeq:" + str(self.current_send_seq) + ";"
                new_data = (header + data_bytes[index:length].decode()).encode()
                m = hashlib.md5()
                m.update(new_data)
                hash_new_data = m.digest() + new_data
                self.send_data[self.current_send_seq] = hash_new_data
                self.current_send_seq += 1
                self.socket.sendto(hash_new_data, (self.dst_ip, self.dst_port))
                # send_packet.append(hash_new_data)
                #time out
                # for p in send_packet:
                #     while not self.ack:
                #         self.socket.sendto(p, (self.dst_ip, self.dst_port))
                #         start = time.time()
                #         while time.time() - start < 0.25:
                #             if self.ack:
                #                 break
                #         # time.sleep(0.01)
                #     self.ack = False
                #     self.current_send_seq += 1

        
    def ack_listener(self):
        #while not self.closed:
            with self.lock:
                #self.lock_send = True
                #if((time.time() - self.time) * 10 % 10 == 0):
                    #print("ack listerner is running")
                    while self.current_send_seq != self.current_ack_seq:
                        print("timer start")
                        start = time.time()
                        original_seq = self.current_ack_seq
                        while time.time() - start < 0.25:
                            if self.current_ack_seq != original_seq:
                                break
                        print(str())
                        if self.current_ack_seq == original_seq:
                                print("resend start")
                                index = self.current_ack_seq
                                print("index is " + str(index))
                                self.socket.sendto(self.send_data[index], (self.dst_ip, self.dst_port))
          
            #self.lock_send = False


    def listener(self):
        while not self.closed:  # a later hint will explain self.closed
                try:
                    #t = Timer(0.1,self.ack_listener)
                    if self.counter == 10:
                        self.counter = 0
                        self.executor.submit(self.ack_listener)
                    self.counter += 1
                    #t.start()
                    # self.ack = False
                    data, addr = self.socket.recvfrom()
                    # store the data in the receive buffer
                    #data_str = data.decode('utf-8')
                    hash = data[0:16]
                    m = hashlib.md5()
                    m.update(data[16:])
                    received_hash = m.digest()
                    if len(data) != 0:
                        if(hash == received_hash):
                            data_str = data[16:].decode()
                            if data_str.split(";")[1] == "ACK":
                                if self.current_ack_seq == int(data_str.split(";")[2].split(":")[1]):
                                    self.ack = True
                                    self.current_ack_seq += 1
                            elif data_str.split(";")[1] == "FIN":
                                    self.fin = True
                            else:
                                seq_number = int(data_str.split(";")[1].split(":")[1])
                                true_data = data_str.split(";")[2].encode()
                                self.recv_buffer[seq_number] = true_data
                                self.seq.append(seq_number)

                                header = ";ACK;" + "DataSeq:" + str(seq_number)
                                m = hashlib.md5()
                                m.update(header.encode())
                                hash_new_data = m.digest() + header.encode()
                                self.socket.sendto(hash_new_data, (self.dst_ip, self.dst_port))

                        else:
                            print("bit drop detect")
                            print(str(received_hash) + " and I get " + str(data))


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


        self.current_recv_seq += 1
        return self.recv_buffer[self.current_recv_seq - 1]


    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        header = ";FIN"
        m = hashlib.md5()
        m.update(header.encode())
        hash_new_data = m.digest() + header.encode()
        self.ack = False
        self.socket.sendto(hash_new_data, (self.dst_ip, self.dst_port))

        # start = time.time()
        # time out
        while not self.ack and not self.fin:
            # start = time.time()
            self.socket.sendto(hash_new_data, (self.dst_ip, self.dst_port))

            # while time.time() - start < 0.25:
            #     if self.ack:
            #         break
        # wait two seconds
        time.sleep(2)
        self.closed = True
        self.socket.stoprecv()

