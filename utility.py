import struct
import codecs

class Info:
    def __init__(self,s_port, r_port, sn, ack_n, ack, fin, window_size, payload,checksum=None):
        self.s_port = s_port
        self.r_port = r_port
        self.sn = sn
        self.ack_n = ack_n
        self.ack = ack
        self.fin = fin
        self.window_size = window_size
        self.payload = payload
        self.checksum = checksum
class Utils:
    def __init__(self):
        self.header_size = 20

    def segment_builder(self, info):

        header_size = self.header_size

        if info.fin:
            flag = 1  # flag field:0000 0001
        else:
            flag = 0  # flag field:0000 0000
        if info.ack:
            flag += 16 # flag field:0001 0000
        checksum = 0
        urgent = 0

        # format string: 'H' means transforming 2-byte int in python to unsigned short in C
        # 'I' means transforming 4-byte int in Python to unsigned int in C
        # 'B' means transforming 1-byte int in Python to unsigned char in C
        raw_segment = raw_header + codecs.encode(info.payload, encoding="utf-16")
        raw_header = struct.pack('!HHIIBBHHH', info.s_port, info.r_port, info.sn, info.ack_n, header_size, flag,
                                 info.window_size, checksum, urgent)

        # calculate checksum (checksum = 0)
        decoded = codecs.decode(raw_segment, encoding="UTF-16")
        checksum = self.CheckSum(decoded)

        # reassemble raw segment (checksum is calculated above)
        full_header = struct.pack("!HHIIBBHHH", info.s_port, info.r_port, info.sn, info.ack_n, header_size, flag,
                                  info.window_size, checksum, urgent)
        full_segment = full_header + codecs.encode(info.payload, encoding="utf-16")

        return full_segment


    # calculate the checksum
    def CheckSum(self, entire_segment):
        #calculate the total summation of 16-bit(2 bytes) values
        payload_len = len(entire_segment) 
        # solve the problem where the length is odd
        if payload_len & 1:
            payload_len -= 1
            sum = ord(entire_segment[payload_len])
        else:
            sum = 0

        # iterate through chars two by two and sum their byte values
        while payload_len > 0:
            payload_len -= 2
            sum += (ord(entire_segment[payload_len + 1]) << 8) + ord(entire_segment[payload_len])
        # wrap overflow around
        sum = (sum >> 16) + (sum & 0xffff)
        res = (~ sum) & 0xffff  # One's complement
        return res

    def unpack(self, segment):

        header = segment[:self.header_size]
        payload = segment[self.header_size:]

        # unpack the package
        s_port, r_port, sn, ack_n, header_size, flag, window_size, CheckSum, urg = struct.unpack(
            "!HHIIBBHHH", header)

        if int(flag % 2 == 1):
            fin = 1  # if flag = 1 or 17, then fin field will be '1'
        else:
            fin = 0

        if (flag >> 4) == 1:
            ack = 1  # if flag = 16, then this segment will be an ACK
        else:
            ack = 0


        # get the payload from the segment
        payload = codecs.decode(payload, encoding="UTF-16")
        new_info = Info(s_port, r_port, sn, ack_n, header_size, ack, fin, window_size, payload,CheckSum)
        return new_info
