import datetime
import sys
import time
from socket import *
from utility import Utils,Info
from standad_vals import TIME_OUT_INTERVAL,ESTIMATED_RTT,DEVIATION,MSS 

class Client:
    def __init__(self, s_file, udpl_addr, udpl_port, inbyte, ack_port):
        """
        Initializes the Client class with necessary parameters.

        Parameters:
        s_file (str): Source file path to read from.
        udpl_addr (str): The IP address of the UDP listener.
        udpl_port (int): The port number of the UDP listener.
        inbyte (int): The size of the window in bytes.
        ack_port (int): The port number to use for receiving ACK packets.
        """

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

        self.inbyte = inbyte #window size inbyte
        self.incount = inbyte // self.MSS #window size incount
        self.ack_port = ack_port

    def buffer_population(self, file):
        """
        Populates the buffer with segments from the source file.

        Parameters:
        file (file): The source file.

        Returns:
        None
        """
        segment_handle = Utils()
        sn = 0
        ack_n = 0

        data = file.read(self.MSS)
        while len(data) > 0:
            next_data = file.read(self.MSS)
            # If next data is empty, means the current data is the final segment
            if len(next_data) == 0:
                info = Info(self.ack_port, self.udpl_port, sn, ack_n, 0, 1,
                                                       self.inbyte, data)
                new_segment = segment_handle.segment_builder(info)
            else:
                info = Info(self.ack_port, self.udpl_port, sn, ack_n, 0, 0,
                                                       self.inbyte, data)
                new_segment = segment_handle.segment_builder(info)
            data = next_data
            ack_n += 1
            sn += 1
            self.buffer.append(new_segment)

    def logger(self, log, status, s_port, d_port, sn, ack_n, header_length, ack, fin,
                  window_size,
                  checkSum, timeout_interval):
        """
        Writes log information to a log file.

        Parameters:
        log (file): The log file to write to.
        status (str): The status of the packet.
        s_port (int): The source port number.
        d_port (int): The destination port number.
        sn (int): The sequence number.
        ack_n (int): The acknowledgement number.
        header_length (int): The length of the packet header.
        ack (int): The acknowledgement flag.
        fin (int): The FIN flag.
        window_size (int): The window size.
        checkSum (str): The packet checksum.
        timeout_interval (int): The timeout interval.

        Returns:
        None
        """

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

    #command line arguments
    try:
        s_file = sys.argv[1]
        udpl_addr = sys.argv[2]
        udpl_port = int(sys.argv[3])
        inbyte = int(sys.argv[4])
        ack_port = int(sys.argv[5])

    except IndexError:
        exit("invalid input format: python3 client.py [filename] [adress_of_udpl] [port_number_of_udpl] ["
             "window_size] [ack_port_number]")

    # create the instance Client
    client = Client(s_file, udpl_addr, udpl_port, inbyte, ack_port)

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
    client.buffer_population(file)

    # create the sending log file descriptor
    try:
        log = open(client.log_file, 'w')
    except IOError:
        print("Client log does not exist")
        sys.exit()

    segment_handle = Utils()

    # initialize window arguments
    lisn = -1 #largest_inorder_sequence_number
    leftBound = 0
    rightBound = client.incount - 1

    # send all segments in window back to back
    for i in range(leftBound, rightBound + 1):

        if i < len(client.buffer):
            sendSocket.sendto(client.buffer[i], (client.udpl_addr, client.udpl_port))
            client.is_resend.append(False)
            client.sender_timestamp.append(time.time())
            
            # write sending log
            sender_info = segment_handle.unpack(client.buffer[i])
            # send_s_port, send_d_port, send_sequenceNumber, send_ackNumber, send_header_length, send_ack, send_fin, send_window_size, send_checkSum, send_data = segment_handle.unpack(
            #     client.buffer[i])
            client.logger(log, "SEND", sender_info.s_port, sender_info.r_port, sender_info.sn, sender_info.ack_n, sender_info.header_size,
                                 sender_info.ack,
                                 sender_info.fin, sender_info.window_size, sender_info.checksum,
                                     client.timeout_interval)

    while lisn < len(client.buffer) - 1:
        j = 0  # flag used to indicate the first timeout segments in all timeout segments sent back to back
        try:
            ackSocket.settimeout(client.timeout_interval)  # set one timer for all packets sent at once
            while lisn < len(client.buffer) - 1:
                ackSegment = ackSocket.recv(2048)
                recieved_info = segment_handle.unpack(ackSegment)
                if recieved_info.ack == 1 and recieved_info.sn == lisn + 1:
                    lisn += 1
                    leftBound += 1
                    rightBound += 1
                    log.write('Move window right by one step.\n')

                    # Update timeout interval when the received ack number corresponds to a non-resent segment
                    # Only update timeout interval for non-resent segments
                    if not client.is_resend[lisn]:
                        sendTime = client.sender_timestamp[lisn]
                        ackTime = time.time()
                        sampleRTT = ackTime - sendTime
                        client.estimatedRTT = 0.875 * client.estimatedRTT + 0.125 * sampleRTT
                        client.deviation = 0.75 * client.deviation + 0.25 * abs(sampleRTT - client.estimatedRTT)
                        client.timeout_interval = client.estimatedRTT + 4 * client.deviation
                        log.write('Calculate timeout interval successfully.\n')

                    print("ACK in count: " + str(lisn) + " sequence number: " + str(
                        lisn * 576) + " received ")

                    # Write receiving log
                    client.logger(log, "RECEIVE", recieved_info.s_port, recieved_info.r_port, recieved_info.sn, recieved_info.ack_n, recieved_info.header_size,
                                 recieved_info.ack,
                                 recieved_info.fin, recieved_info.window_size, recieved_info.checksum,
                                     client.timeout_interval)

                    # send non-transmitted segment in the window since window move right
                    if rightBound < len(client.buffer):
                        ackSocket.sendto(client.buffer[rightBound], (client.udpl_addr, client.udpl_port))
                        client.is_resend.append(False)
                        client.sender_timestamp.append(time.time())
                        ackSocket.settimeout(client.timeout_interval)

                        # Write sending log
                        send_info = segment_handle.unpack(
                            client.buffer[rightBound])
                        client.logger(log, "SEND", send_info.s_port, send_info.r_port, send_info.sn, send_info.ack_n, send_info.header_size,
                                 send_info.ack,
                                 send_info.fin, send_info.window_size, send_info.checksum, client.timeout_interval)
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
                    send_info = segment_handle.unpack(
                        client.buffer[i])
                    client.logger(log, "RESEND", send_info.s_port, send_info.r_port, send_info.sn, send_info.ack_n, send_info.header_size,
                                 send_info.ack,
                                 send_info.fin, send_info.window_size, send_info.checksum, client.timeout_interval)

    sendSocket.close()
    ackSocket.close()
