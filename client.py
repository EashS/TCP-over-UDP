import datetime
import sys
import time
from socket import *
from utility import Utils,Info
from standad_vals import TIME_OUT_INTERVAL,ESTIMATED_RTT,DEVIATION,MSS 

class CustomClient:
    def __init__(self, s_file, udpl_addr, udpl_port, win_size_inbyte, ack_port):
        self.is_resend = []
        self.sender_timestamp = []
        self.buffer = []  # read from source file
        self.MSS = MSS  # one segment contains 576 characters, because 1 character is 1 byte in 'utf-16'
        self.s_file = s_file

        self.log_file = "client_log.txt"

        self.udpl_addr = udpl_addr
        self.udpl_port = udpl_port

        self.timeout_interval = TIME_OUT_INTERVAL
        self.estimatedRTT = ESTIMATED_RTT
        self.deviation = DEVIATION

        self.win_size_inbyte = win_size_inbyte
        self.win_size_incount = win_size_inbyte // self.MSS
        self.ack_port = ack_port

    def populate_buffer(self, file):

        segment_handle = Utils()
        sn = 0
        ack_n = 0

        data = file.read(self.MSS)
        while len(data) > 0:
            next_data = file.read(self.MSS)
            # If next data is empty, means the current data is the final segment
            if len(next_data) == 0:
                info = Info(self.ack_port, self.udpl_port, sn, ack_n, 0, 1,
                                                       self.win_size_inbyte, data)
                new_segment = segment_handle.segment_builder(info)
            else:
                info = Info(self.ack_port, self.udpl_port, sn, ack_n, 0, 0,
                                                       self.win_size_inbyte, data)
                new_segment = segment_handle.segment_builder(info)
            data = next_data
            ack_n += 1
            sn += 1
            self.buffer.append(new_segment)

    def logger(self, log, status, s_port, d_port, sn, ack_n, header_length, ack, fin,
                  window_size,
                  checkSum, timeout_interval):
        content = "[" + status + " - " + "Time: " + str(datetime.datetime.now()) + " - source port: " + str(
            s_port) + \
                  " - dest port: " + str(d_port) + " - sequence number: " + str(sn) + \
                  " - ack number: " + str(ack_n) + " - header length: " + str(header_length) + \
                  " - ACK: " + str(ack) + " - FIN: " + str(fin) + " - window size: " + str(window_size) + \
                  " - checksum: " + str(checkSum)
        if status == "SEND" or status == "RESEND":
            content += " - timeout interval: " + str(timeout_interval)
        content += "]\n"
        log.write(content)


# Main Method ---------------------------------------------
if __name__ == '__main__':

    # reading command line arguments
    try:
        s_file = sys.argv[1]
        udpl_addr = sys.argv[2]
        udpl_port = int(sys.argv[3])
        win_size_inbyte = int(sys.argv[4])
        ack_port = int(sys.argv[5])

    except IndexError:
        exit("Please input as follows: python3 client.py [filename] [adress_of_udpl] [port_number_of_udpl] ["
             "window_size] [ack_port_number]")

    # create the instance CustomClient
    client = CustomClient(s_file, udpl_addr, udpl_port, win_size_inbyte, ack_port)

    # initiate sockets
    sendSocket = socket(AF_INET, SOCK_DGRAM)
    ackSocket = socket(AF_INET, SOCK_DGRAM)
    ackSocket.bind(('localhost', client.ack_port))

    # read from source file and populate the segment buffer
    try:
        file = open(client.s_file, 'r')
    except IOError:
        print("Source file does not exist")
        sendSocket.close()
        ackSocket.close()
        sys.exit()
    client.populate_buffer(file)

    # create the sending log file descriptor
    try:
        log = open(client.log_file, 'w')
    except IOError:
        print("Client log does not exist")
        sys.exit()

    segment_handle = Utils()

    # initialize window arguments
    largest_inorder_sequence_number = -1
    leftBound = 0
    rightBound = client.win_size_incount - 1

    # send all segments in window back to back
    for i in range(leftBound, rightBound + 1):

        if i < len(client.buffer):
            sendSocket.sendto(client.buffer[i], (client.udpl_addr, client.udpl_port))
            client.is_resend.append(False)
            client.sender_timestamp.append(time.time())

            # write sending log
            send_s_port, send_d_port, send_sequenceNumber, send_ackNumber, send_header_length, send_ack, send_fin, send_window_size, send_checkSum, send_data = segment_handle.unpack_segment(
                client.buffer[i])
            client.logger(log, "SEND", send_s_port, send_d_port, send_sequenceNumber, send_ackNumber,
                             send_header_length, send_ack, send_fin, send_window_size, send_checkSum,
                             client.timeout_interval)

    while largest_inorder_sequence_number < len(client.buffer) - 1:
        j = 0  # flag used to indicate the first timeout segments in all timeout segments sent back to back
        try:
            ackSocket.settimeout(client.timeout_interval)  # set one timer for all packets sent at once
            while largest_inorder_sequence_number < len(client.buffer) - 1:
                ackSegment = ackSocket.recv(2048)
                ack_s_port, ack_d_port, ack_sequenceNumber, ack_ackNumber, ack_header_length, ack_ack, ack_fin, ack_window_size, ack_checkSum, ack_data = segment_handle.unpack_segment(
                    ackSegment)
                if ack_ack == 1 and ack_sequenceNumber == largest_inorder_sequence_number + 1:
                    largest_inorder_sequence_number += 1
                    leftBound += 1
                    rightBound += 1
                    log.write('Move window right by one step.\n')

                    # Update timeout interval when the received ack number corresponds to a non-resent segment
                    # Only update timeout interval for non-resent segments
                    if not client.is_resend[largest_inorder_sequence_number]:
                        sendTime = client.sender_timestamp[largest_inorder_sequence_number]
                        ackTime = time.time()
                        sampleRTT = ackTime - sendTime
                        client.estimatedRTT = 0.875 * client.estimatedRTT + 0.125 * sampleRTT
                        client.deviation = 0.75 * client.deviation + 0.25 * abs(sampleRTT - client.estimatedRTT)
                        client.timeout_interval = client.estimatedRTT + 4 * client.deviation
                        log.write('Calculate timeout interval successfully.\n')

                    print("ACK in count: " + str(largest_inorder_sequence_number) + " sequence number: " + str(
                        largest_inorder_sequence_number * 576) + " received ")

                    # Write receiving log
                    client.logger(log, "RECEIVE", ack_s_port, ack_d_port, ack_sequenceNumber, ack_ackNumber,
                                     ack_header_length, ack_ack, ack_fin, ack_window_size, ack_checkSum,
                                     client.timeout_interval)

                    # send non-transmitted segment in the window since window move right
                    if rightBound < len(client.buffer):
                        ackSocket.sendto(client.buffer[rightBound], (client.udpl_addr, client.udpl_port))
                        client.is_resend.append(False)
                        client.sender_timestamp.append(time.time())
                        ackSocket.settimeout(client.timeout_interval)

                        # Write sending log
                        send_s_port, send_d_port, send_sequenceNumber, send_ackNumber, send_header_length, send_ack, send_fin, send_window_size, send_checkSum, send_data = segment_handle.unpack_segment(
                            client.buffer[rightBound])
                        client.logger(log, "SEND", send_s_port, send_d_port, send_sequenceNumber,
                                         send_ackNumber, send_header_length, send_ack, send_fin, send_window_size,
                                         send_checkSum, client.timeout_interval)
        except timeout:
            # resend all segments in window once time out
            for i in range(leftBound, rightBound + 1):
                if i < len(client.buffer):
                    sendSocket.sendto(client.buffer[i], (client.udpl_addr, client.udpl_port))
                    client.is_resend[i] = True

                    # Double the timeout interval only if this is the first segment in all timeout segments sent back
                    # to back
                    if j == 0:
                        client.timeout_interval *= 2
                        j += 1
                    log.write("One Segment Transmit Timeout! Double the timeout interval only if this is the first "
                              "time in this "
                              "transmission.\n")
                    client.sender_timestamp[i] = time.time()

                    # Write resending log
                    send_s_port, send_d_port, send_sequenceNumber, send_ackNumber, send_header_length, send_ack, send_fin, send_window_size, send_checkSum, send_data = segment_handle.unpack_segment(
                        client.buffer[i])
                    client.logger(log, "RESEND", send_s_port, send_d_port, send_sequenceNumber,
                                     send_ackNumber, send_header_length, send_ack, send_fin, send_window_size,
                                     send_checkSum, client.timeout_interval)

    sendSocket.close()
    ackSocket.close()
