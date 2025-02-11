#
#      TFTP Client with option extension
#
#    Written by Jusper Angelo M. Cesar, S13
#
#
# In compliance with NSCOM01 MCO1 Specification
#
# RFC - 
# RFC - 
# RFC - 
# RFC - 


# TO DO 
#
#           ROUTE THE ERROR CODES
#           REFACTOR THE CODE
#           AND THEN MAKE SURE YOU FOLLOW PROTOCOL
#
#
#
#



import socket as soc
import os
import struct as st
import re


# The first port used
TFTP_Port = 69
IPv4_PTRN = r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]?|0)\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]?|0)$"

"""
   0         Not defined, see error message (if any).
   1         File not found.
   2         Access violation.
   3         Disk full or allocation exceeded.
   4         Illegal TFTP operation.
   5         Unknown transfer ID.
   6         File already exists.
   7         No such user.
"""

class Clientv2:
   
    def __init__(self):
        self.destIP =  "192.168.59.1"
        self.sock = soc.socket(soc.AF_INET, soc.SOCK_DGRAM)
        self.sock.settimeout(5)
        self.running = True
        self.start()

    def start(self):
        print("TFTP Client")
        while self.running:
            user_input = input(">>").strip()
            self.switchCase(user_input)

    def switchCase(self, input):
        command = None
        if input:
            command = input.split()[0]

        match command:
            case "select":
                if(len(input.split()) == 2):
                    self.connect(input.split()[1])
                else:
                    print("Invalid Syntax Error: select [ip]")
            case "/close":
                print("call close function")
            case "/?":
                self.help()
            case "put":
                self.sendReq("chama.jpg")
            case "get":
                self.defReq("chama.jpg")
            case _:
                print("Invalid command.")
                    
    #
    #   Writing to the server
    #   
    # 
    #   
    # 
    def sendReq(self, filename, blksize=512, tsize=False):
        
        # Validation

        if blksize <=  0 or blksize > 65464:
            print(f"[ERR] Block size is not in range [0:65464]: {blksize}")
            return
            
        if not os.path.exists(filename):
            print(f"[ERR] File does not exist: {filename}")
            return
        
        # First contact

        packet = b"\x00\x02" + filename.encode() + b"\x00" + b"octet" + b"\x00"

        if tsize != False:
            filesize = os.path.getsize(filename)
            packet += b"tsize" + b"\x00" + str(filesize).encode() + b"\x00"

        if blksize != 512:
            packet += b"blksize" + b"\x00" + str(blksize).encode() + b"\x00"
        
        self.sock.sendto(packet, (self.destIP, TFTP_Port))
        print(f"[INF] Sending {packet} to {self.destIP}, {TFTP_Port}...")

        try:
            r_packet, tid  = self.sock.recvfrom(512)
            print(f"[INF] Received {r_packet} from {tid}...")
        except Exception as e:
            print(f"[ERR] Failed to receive data: {e}")
            return

        # AGAIN CHECK IF THEY MATCH
        # check for no. 6

        opcode = int.from_bytes(r_packet[0:2], "big")

        if opcode == 5:
            print(f"[ERR] Error code has been received: Terminating process.")
            return
        
        if opcode == 4:
            blksize = 512
            tsize = False
            print(f"[WRN] The options were discarded.")
        

        if opcode == 6:
            data = r_packet[2:]
            
            seen_options = set()
            while data:
                try:
                    name, data = data.split(b"\x00", 1)
                    name = name.decode("ascii")
                    value, data = data.split(b"\x00", 1)
                    value_int = int(value.decode())
                    if name in seen_options:
                        print(f"[ERR] Duplicate option detected: {name}")
                        return 
                    if name == "tsize":
                        tsize = value_int
                    elif name == "blksize":
                        blksize = value_int

                    seen_options.add(name)

                except ValueError:
                    print("[ERR] Malformed OACK packet")
                    return None 

            if "tsize" not in seen_options:
                tsize = 0
            if "blksize" not in seen_options:
                blksize = 512

        

        

    def defReq(self, filename, blksize=512, tsize=False):

        #Validation

        if blksize <=  0 | blksize > 65464:
            print(f"[ERR] Block size is not in range [0:65464]: {blksize}")
            return
        
        # First Contact

        packet = st.pack("!H", 1) +  filename.encode("ascii") +  "\x00".encode() +  "octet".encode("ascii") +  "\x00".encode()

        if blksize != 512:
            packet += b"blksize" + b"\x00" + str(blksize).encode() + b"\x00"

        if tsize != False:
            tsize = 0
            packet += b"tsize" + b"\x00" + str(tsize).encode() + "\x00"

        self.sock.sendto(packet, (self.destIP, TFTP_Port))
        self.sock.settimeout(5)
        print(f"[INF] Sending {packet} to {self.destIP}, {TFTP_Port}...")
        
        try:
            r_packet, tid  = self.sock.recvfrom(blksize + 4)
            print(f"[INF] Received {r_packet} from {tid}...")
        except Exception as e:
            print(f"[ERR] Failed to receive data: {e}")
            return
        
        opcode = int.from_bytes(r_packet[0:2], "big")

        if opcode == 3:
            with open(filename, "wb") as file:
                i = 1
                while True:
                    packet = None
                    packet = st.pack("!H", 4) + i.to_bytes(2, "big")

                    
                    self.sock.sendto(packet, tid)
                    print(f"[INF] Sending {packet} to {tid}...")

                    r_packet, tid =  self.sock.recvfrom(blksize +  4)
                    # print(f"[INF] Received {r_packet} from {tid}...")

                    opcode = st.unpack("!H", r_packet[0:2])[0]
                    if opcode == 5:
                        print("[ERR] Error code has been received: Terminating process.")
                        break

                    file.write(r_packet[4:])

                    if len(r_packet) < blksize:
                        print(f"[INF] {filename} has been received succesfully.")
                        i+=1
                        break
                    i+=1
                packet = st.pack("!H", 4) + i.to_bytes(2, "big")
                self.sock.sendto(packet, tid)
            
            return



        if opcode == 5:
            print(f"[ERR] Error code has been received: Terminating process.")
            return
      
        if opcode == 6:
            data = r_packet[2:]
            
            seen_options = set()
            while data:
                try:
                    name, data = data.split(b"\x00", 1)
                    name = name.decode("ascii")
                    value, data = data.split(b"\x00", 1)
                    value_int = int(value.decode())
                    if name in seen_options:
                        print(f"[ERR] Duplicate option detected: {name}")
                        return 
                    if name == "tsize":
                        tsize = value_int
                    elif name == "blksize":
                        blksize = value_int

                    seen_options.add(name)

                except ValueError:
                    print("[ERR] Malformed OACK packet")
                    return None 

            if "tsize" not in seen_options:
                tsize = 0
            if "blksize" not in seen_options:
                blksize = 512
        
            start = 1
                
            if tsize != 0 or blksize != 512:
                start = 0
            with open(filename, "wb") as file:
                i = start
                while True:
                    packet = None
                    packet = st.pack("!H", 4) + i.to_bytes(2, "big")

                    
                    self.sock.sendto(packet, tid)
                    print(f"[INF] Sending {packet} to {tid}...")

                    r_packet, tid =  self.sock.recvfrom(blksize +  4)
                    # print(f"[INF] Received {r_packet} from {tid}...")

                    opcode = st.unpack("!H", r_packet[0:2])[0]
                    if opcode == 5:
                        print("[ERR] Error code has been received: Terminating process.")
                        break

                    file.write(r_packet[4:])

                    if len(r_packet) < blksize:
                        print(f"[INF] {filename} has been received succesfully.")
                        i+=1
                        break
                    i+=1
                packet = st.pack("!H", 4) + i.to_bytes(2, "big")
                self.sock.sendto(packet, tid)

if __name__ == "__main__":
    c = Clientv2()