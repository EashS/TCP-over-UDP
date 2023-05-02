import codecs
import struct
import sys
import datetime
from socket import *
from utility import Utils, Info

class Server:
    def __init__(self, dest_file, listening_port, ack_address, ack_port):
        self.dest_file = dest_file
        self.log_file = "server_logs.txt"
        self.listening_port = listening_port
        self.ack_address = ack_address
        self.ack_port = ack_port

    def logger(self, log, status, s_port, d_port, sn, ack_n,header_size, ack, fin,
                  window_size,
                  checkSum):
        content = "[" + status + " - " + "Time: " + str(datetime.datetime.now()) + " - source port: " + str(
            s_port) + \
                  " - dest port: " + str(d_port) + " - sequence number: " + str(sn) + \
                  " - ack number: " + str(ack_n) + " - header length: " + str(header_size) + \
                  " - ACK: " + str(ack) + " - FIN: " + str(fin) + " - window size: " + str(window_size) + \
                  " - checksum: " + str(checkSum) + "]\n"
        log.write(content)


# Main Method ---------------------------------------------

if __name__ == '__main__':
    # read from the command line
    try:
        destination_file = sys.argv[1]
        listening_port = int(sys.argv[2])
        ack_address = str(sys.argv[3])
        ack_port = int(sys.argv[4])

    except IndexError:
        exit(
            "Invalid command: python3 server.py [filename] [listening_port] [address_for_acks] [port_for_acks]")

    server = Server(destination_file, listening_port, ack_address, ack_port)

    # Initiate sockets
    receiveSocket = socket(AF_INET, SOCK_DGRAM)
    receiveSocket.bind(('localhost', server.listening_port))
    ackSocket = socket(AF_INET, SOCK_DGRAM)

    # create destination file descriptor
    try:
        file = open(server.dest_file, 'w')
    except IOError:
        print("Destination file does not exist")
        receiveSocket.close()
        ackSocket.close()
        sys.exit()

    # create sever log file file descriptor
    try:
        log = open(server.log_file, 'w')
    except IOError:
        print("Server log does not exist")
        sys.exit()

    # receive segments and send ACK
    segment_handle = Utils()
    largest_inorder_sn = -1
    flag = True

    while flag:
        segment, clientAddress = receiveSocket.recvfrom(2048)

        if segment:
            # Unpack the received segment
            info = segment_handle.unpack_segment(
                segment)

            # Prepare to check if segment has been corrupted and received in order
            header_length = 20
            flags = (info.ack << 4) + info.fin
            raw_header = struct.pack('!HHIIBBHHH', info.s_port, info.r_port, info.sn, info.ack_n, header_length,
                                     flags, info.window_size, 0, 0)
            raw_segment = raw_header + codecs.encode(info.payload, encoding="utf-16")
            decoded_msg = codecs.decode(raw_segment, encoding="utf-16")
            
            payload_len = len(decoded_msg)
            # solve the problem where the length is odd
            if payload_len & 1:
                payload_len -= 1
                sum = ord(decoded_msg[payload_len])
            else:
                sum = 0

            # iterate through chars two by two and sum their byte values
            while payload_len > 0:
                payload_len -= 2
                sum += (ord(decoded_msg[payload_len + 1]) << 8) + ord(decoded_msg[payload_len])
            # wrap overflow around
            sum = (sum >> 16) + (sum & 0xffff)

            # If no error introduced, then the sum should be 0xffff (65535 in decimal)
            if (sum + info.checksum == 65535 and info.sn == largest_inorder_sn + 1):
                if info.fin:
                    file.write(info.payload.rstrip())
                    flag = False
                else:
                    file.write(info.payload)

                # Send ack to client
                largest_inorder_sn += 1
                new_info = Info(server.listening_port, server.ack_port,
                                                          largest_inorder_sn,
                                                          largest_inorder_sn + 1, 1, 0, info.window_size, "")
                ackSegment = segment_handle.segment_builder(new_info)
                ackSocket.sendto(ackSegment, (server.ack_address, server.ack_port))

                # Write server log
                server.logger(log, "RECEIVE", info.s_port, info.r_port, info.sn, info.ack_n, header_length,
                                 info.ack,
                                 info.fin, info.window_size, info.checksum)

                send_info = segment_handle.unpack_segment(
                    ackSegment)
                server.logger(log, "SEND", send_info.s_port, send_info.r_port, send_info.sn, send_info.ack_n, header_length,
                                 send_info.ack,
                                 send_info.fin, send_info.window_size, send_info.checksum)

    receiveSocket.close()
    ackSocket.close()
