import struct
import codecs

class Info:
    """
    A class representing the information contained in a TCP segment
    """
    def __init__(self,s_port, r_port, sn, ack_n,ack, fin, window_size, payload,checksum=None,header_size=None):
        """
        Initializes the Info object with the given attributes

        Args:
        s_port (int): Source port number
        r_port (int): Destination port number
        sn (int): Sequence number
        ack_n (int): Acknowledgement number
        ack (int): Acknowledgement flag (1 if present, 0 otherwise)
        fin (int): Finish flag (1 if present, 0 otherwise)
        window_size (int): Size of the window in bytes
        payload (str): Data payload in the segment
        checksum (int, optional): Checksum value of the segment (defaults to None)
        header_size (int, optional): Size of the header in bytes (defaults to None)
        """

        self.s_port = s_port
        self.r_port = r_port
        self.sn = sn
        self.header_size = header_size
        self.ack_n = ack_n
        self.ack = ack
        self.fin = fin
        self.window_size = window_size
        self.payload = payload
        self.checksum = checksum
class Utils:
    """
    A class containing utility methods for building and unpacking TCP segments
    """

    def __init__(self):
        """
        Initializes the Utils object with a default header size of 20 bytes
        """

        self.header_size = 20

    def segment_builder(self, info):
        """
        Builds a TCP segment using the given information

        Args:
        info (Info): An Info object containing the necessary attributes to build a segment

        Returns:
        bytes: A byte string representing the TCP segment
        """

        header_size = self.header_size

        # Determine the flag value based on the presence of the FIN and ACK flags
        if info.fin:
            flag = 1  # flag field:0000 0001
        else:
            flag = 0  # flag field:0000 0000
        if info.ack:
            flag += 16 # flag field:0001 0000
        checksum = 0
        urgent = 0

        # Pack the header using the given information
        # 'H':transforming 2-byte int to unsigned short in C
        # 'I':  transforming 4-byte int  to unsigned int in C
        # 'B' : transforming 1-byte int  to unsigned char in C
        raw_header = struct.pack('!HHIIBBHHH', info.s_port, info.r_port, info.sn, info.ack_n, header_size, flag,
                                 info.window_size, checksum, urgent)

        # Encode the payload in utf-16 and append it to the header
        raw_segment = raw_header + codecs.encode(info.payload, encoding="utf-16")

        # calculate checksum (checksum = 0)
        decoded = codecs.decode(raw_segment, encoding="UTF-16")
        checksum = self.CheckSum(decoded)

        # Repack the header with the calculated checksum and reassemble the segment
        full_header = struct.pack("!HHIIBBHHH", info.s_port, info.r_port, info.sn, info.ack_n, header_size, flag,
                                  info.window_size, checksum, urgent)
        full_segment = full_header + codecs.encode(info.payload, encoding="utf-16")

        return full_segment


    # calculate the checksum
    def CheckSum(self, entire_segment):
        """
        Calculates the checksum for the given TCP segment

        Args:
        entire_segment (str): The TCP segment to calculate the checksum for

        Returns:
        int: The calculated checksum
        """

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
        """This method takes a byte string and unpacks it to obtain the values of the fields in the header and the payload.
        It returns an object of the Info class that encapsulates these values.

        Args:
            segment (bytes): A byte string representing a TCP segment.

        Returns:
            Info: An object of the Info class that contains the values of the fields in the header and the payload.

        Raises:
            None.
        """

        # separate the header and the payload from the segment
        header = segment[:self.header_size]
        payload = segment[self.header_size:]

        # determine the values of the 'fin' and 'ack' fields from the 'flag' field
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


        # decode the payload from UTF-16 to Unicode string
        payload = codecs.decode(payload, encoding="UTF-16")
        # create an object of the Info class to encapsulate the values of the fields in the header and the payload
        new_info = Info(s_port, r_port, sn, ack_n, ack, fin, window_size, payload,CheckSum,header_size)
        return new_info
