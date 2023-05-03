# Simple-TCP-over-UDP
Step 1: Start the NEWUDPL emulator.

Format: ./newudpl [-i source_host:port/*] [-o dest_host:port/*] [-L random_pack_loss_rate] [-B bit_error_rate] [-O out_of_order_rate] [-d delay]
Command: ./newudpl -i 'localhost':'*' -o 'localhost':41194 -L 12 -B 3 -O 20 -d 0.3 -vv
Step 2: Start the server.py with the port number that you want to use, and also other parameters:

Format: python3 [tcpserver] [file] [listening_port] [address_for_acks] [port_for_acks]
Command: python3 server.py received_file.txt 41194 localhost 40000
Step 3: Start the client.py.

Format: python3 [tcpclient] [file] [address_of_udpl] [port_number_of_udpl] [windowsize] [ack_port_number]
Command: python3 client.py source_file.txt localhost 41192 1728 40000
BTW: The window size is measured in byte, I set