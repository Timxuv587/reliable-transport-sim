# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
import struct

class Streamer:
    def __init__(self, dst_ip, dst_port,
                 src_ip=INADDR_ANY, src_port=0, recv_buffer=[None*1000]):
        """Default values listen on all network interfaces, chooses a random source port,
           and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.recv_buffer = recv_buffer

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!

        # for now I'm just sending the raw application-level data in one UDP payload
        length = len(data_bytes)

        index = 0
        sequence_num = 0
        # # create recv_buffer
        # recv_buffer = []
        while length - index > 1472:
            header = "Seq: " + sequence_num + " "
            data = data_bytes[index:index+1472]
            new_data = struct.pack(header,data)
            self.socket.sendto(new_data, (self.dst_ip, self.dst_port))
            index += 1472
            sequence_num += 1

        new_data = struct.pack(header, data_bytes[index:length])
        self.socket.sendto(new_data, (self.dst_ip, self.dst_port))

        

    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
        
        # this sample code just calls the recvfrom method on the LossySocket
        data, addr = self.socket.recvfrom()
        # TODO: needs to solve
        # if len(self.recv_buffer) < len(data):
        #     self.recv_buffer = [None*len(data)]

        data_str = struct.unpack(data).decode('utf-8')
        seq_number = int(data_str.split(" ")[1])
        true_data = data_str.split(" ")[2].encode('utf-8')
        self.recv_buffer[seq_number] = true_data
        # For now, I'll just pass the full UDP payload to the app
        if None not in self.recv_buffer:
            return None
        return data

    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        pass
