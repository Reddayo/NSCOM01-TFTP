
# Written by reddayo

# Issues.
# Error code 5 has not been made
# Error code 8 has not been made
# The following is a piece of unrefactored horse manure code
# OACK IS NOT FULLY DONE - WE DONT HAVE CODE TO SEND OACK IN CASE WE NEED TO TO THE SERVER
# TURN THIS MFER INTO KEYS AND VALUES

import socket as soc
import os
import struct as st
import re


# First destination port to be used for transfer
TFTP_Port = 69

# Pattern for IPv4
IPv4_PTRN = r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]?|0)\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]?|0)$"


# blksize having a default value of 512
#  tsize is the file size, that's why it's either included or not, a boolean

# Error codes

class Clientv3:

    def __init__(self):
        self.destIP =  "192.168.59.1"
        self.sock = soc.socket(soc.AF_INET, soc.SOCK_DGRAM)
        self.sock.settimeout(5)
        self.running = True
        self.start()

    def start(self):
        print("Welcome to the TFTP Client")
        print("Client Version 3.2")
        print("Author: Jusper Angelo Cesar")
        print("")
        print("No destination IP set. Use 'set-dest' to configure.")
        print("Type ? for help.")
        while self.running:
            user_input = input(">> ").strip()
            self.switchCase(user_input)


    # Parsing user input

    def switchCase(self, user_input):
        tokens = user_input.split()

        if not tokens:
            print("[ERR] No command entered.")
            return

        command = tokens[0].lower()
        args = tokens[1:]

        command_map = {
            "put": self.put,
            "get": self.get,
            "set-dest": self.set_dest,
            "show-dest": self.show_dest,
            "?": self.help,
            "close": self.close_connection,
        }

        if command not in command_map:
            print("[ERR] Invalid command. Use '?' for help.")
            return

        if command in {"put", "get"}:
            if len(args) < 1:
                print(f"[ERR] Invalid Syntax: {command} [filename] [options]")
                return

            filename = None
            blksize = 512
            tsize = False
            seen_flags = set()

            i = 0
            while i < len(args):
                arg = args[i]

                if arg == "-b":
                    if "blksize" in seen_flags:
                        print("[ERR] Duplicate blksize flag detected.")
                        return
                    if i + 1 >= len(args) or not args[i + 1].isdigit():
                        print("[ERR] Missing or invalid blksize value.")
                        return
                    blksize = int(args[i + 1])
                    seen_flags.add("blksize")
                    
                    if blksize <  8 or blksize > 65464:
                        print(f"[ERR] Block size is not in range [8:65464]: {blksize}")
                        return
                    
                    i += 1

                elif arg == "-t":
                    if "tsize" in seen_flags:
                        print("[ERR] Duplicate tsize flag detected.")
                        return
                    tsize = True
                    seen_flags.add("tsize")

                elif filename is None:  # First argument (filename)
                    filename = arg

                else:
                    print(f"[ERR] Unknown option: {arg}")
                    return

                i += 1

            if filename is None:
                print(f"[ERR] Invalid Syntax: {command} [filename] [options]")
                return

            command_map[command](filename, blksize, tsize)

        elif command == "set-dest":
            if len(args) != 1:
                print("[ERR] Invalid Syntax: set-dest [ip]")
                return
            command_map[command](args[0])

        else:
            command_map[command]()
            
        
    # Error messages
    def errorHandler(self, error_packet: bytes):
        opcode = int.from_bytes(error_packet[0:2], "big")

        if opcode != 5:
            print("[ERR] Packet is not an error packet.")
            return

        error_code = int.from_bytes(error_packet[2:4], "big")
        error_msg = error_packet[4:].decode().strip("\x00")

        error_meanings = {
            0: "Not defined, see error message",
            1: "File not found",
            2: "Access violation",
            3: "Disk full or allocation exceeded",
            4: "Illegal TFTP operation",
            5: "Unknown transfer ID",
            6: "File already exists",
            7: "No such user",
            8: "Denied option negotiation"
        }
        # I know that 5 should not terminate the process
        error_meaning = error_meanings.get(error_code, "Unknown error code")
        print(f"[ERR] Code {error_code}: {error_meaning}. Message: {error_msg}")
        print(f"[INF] Terminating process...")

    # Middleware

    def requestMaker(self, opcode: int, filename: str, options: dict = None) -> bytes:
        
        if opcode not in (1, 2):
            raise ValueError("[ERR] Invalid opcode. Must be 1 (RRQ) or 2 (WRQ).")

        packet = opcode.to_bytes(2, "big") + filename.encode() + b"\x00" + b"octet" + b"\x00"

        if options:
            packet += self.buildOptions(options)

        print(f"[INF] Sending {packet} to ({self.destIP}, {TFTP_Port})...")
        return packet
    
    def buildOptions(self, options: dict) -> bytes:
  
        packet = b""

        for option, value in options.items():
            packet += option.encode() + b"\x00" + str(value).encode() + b"\x00"

        return packet
    
    
    def getFiles(self, start, filename, r_packet, tid, blksize):
        with open(filename, "wb") as file:
            # OACK starts at 0, DATA starts at 1
            if start == 1:
                file.write(r_packet[4:])
            while True:
                r_packet = st.pack("!H", 4) + start.to_bytes(2, "big")

                self.sock.sendto(r_packet, tid)
                print(f"[INF] Sending {r_packet} to ({tid})...")
                print(f"[CUR] Block {start}")
                r_packet, tid =  self.sock.recvfrom(blksize + 4)
                # print(f"[INF] Received {r_packet} from {tid}...")

                opcode = st.unpack("!H", r_packet[0:2])[0]

                if opcode == 5:
                    self.errorHandler(r_packet)
                    return
                
                file.write(r_packet[4:])
                
                if len(r_packet) < blksize + 4:
                    print(f"[INF] {filename} has been received succesfully.")
                    start+=1
                    break
                
                start+=1
            packet = st.pack("!H", 4) + start.to_bytes(2, "big")
            self.sock.sendto(packet, tid)

    # ADD A CLAUSE AND KILL THE PROCESS WHEN BLKSIZE IS BIGGER
    def oackHandler(self, data, options):
        seen_options = set()
        while data:
            try:
                name, data = data.split(b"\x00", 1)
                name = name.decode("ascii")

                if not data:
                    print("[ERR] Malformed OACK packet (missing value)")
                    return None

                value, data = data.split(b"\x00", 1)
                try:
                    value_int = int(value.decode())
                except ValueError:
                    print(f"[ERR] Invalid value for option {name}: {value}")
                    return None

                if name in seen_options:
                    print(f"[ERR] Duplicate option detected: {name}")
                    return None

                options[name] = value_int
                seen_options.add(name)

            except ValueError:
                print("[ERR] Malformed OACK packet")
                return None

        if "tsize" not in options:
            options["tsize"] = 0
        if "blksize" not in options:
            options["blksize"] = 512

        return options

    # Check Packet

    
    # We could allso build a function that controls both the requests, and they only differ at the end of their lifetime
  
    
    # Commands

    def put(self, filename, blksize, tsize):
        # Build the WRQ packet

        if not os.path.exists(filename):
            print(f"[ERR] File does not exist: {filename}")
            return
        print(f"[INF] File exists. Proceeding with transfer.")
        options = {}

        if blksize != 512:
            options["blksize"] = blksize

        if tsize:
            options["tsize"] = os.path.getsize(filename)

        # Send the WRQ packet 
        self.sock.sendto(self.requestMaker(2, filename, options), (self.destIP, TFTP_Port))
        
        # Receive OACK/ACK/ERROR packet
        try:
            r_packet, tid  = self.sock.recvfrom(512 + 4)
            print(f"[INF] Received {r_packet} from {tid}...")
        except Exception as e:
            print(f"[ERR] Failed to receive data: {e}")
            return
        
        # Check the opcode, CHECK FOR ERROR CODES
        opcode = int.from_bytes(r_packet[0:2], "big")
        
        if opcode == 4:
            blksize = 512
            tsize = False # HANDLE THIS SOMEHOW, LIKE ADD A STORAGE THINGY WITHTHIS
            if options:
                print(f"[WRN] The options {options} were discarded.")

        if opcode == 5:
            self.errorHandler(r_packet)
            return
        
        if opcode == 6:
            options = self.oackHandler(r_packet[2:], options)
            blksize = options["blksize"]
            tsize = options["tsize"]

        with open(filename, "rb") as file:
            i = 1 
            while chunk := file.read(blksize):
                while True:
                    pck = st.pack("!H", 3) + i.to_bytes(2, "big") + chunk
                    self.sock.sendto(pck, tid)
                    print(f"[INF] Start process: Sending file...{filename}")
                    try:
                        self.sock.settimeout(2)
                        h, a = self.sock.recvfrom(blksize)
                    except soc.timeout:
                        print(f"[WARN] Timeout, resending block {i}...")
                        continue

                    print(f"[INF] Received {h} from {a}...")

                    ope = int.from_bytes(h[0:2], "big")
                    ack_block = int.from_bytes(h[2:4], "big")

                    if ope == 5:
                        self.errorHandler(h)
                        return

                    if ope == 4:
                        if ack_block == i:
                            print(f"[INF] Received correct ACK for block {i}")
                            break 
                        else:
                            print(f"[WARN] Duplicate/old ACK {ack_block}, resending block {i}...")
                i += 1

        # Process the received packet

    def get(self, filename, blksize, tsize):
        # Build the RRQ packet
        options = {}

        if blksize != 512:
            options["blksize"] = blksize

        if tsize:
            options["tsize"] = 0

        # Send the RRQ packet 
        self.sock.sendto(self.requestMaker(1, filename, options), (self.destIP, TFTP_Port))
        
        # Receive OACK/ACK/ERROR packet

        try:
            r_packet, tid  = self.sock.recvfrom(blksize + 4)
            print(f"[INF] Received {r_packet} from {tid}...")
        except Exception as e:
            print(f"[ERR] Failed to receive data: {e}")
            return
        
        opcode = int.from_bytes(r_packet[0:2], "big")

        if opcode == 3:
           self.getFiles(1, filename, r_packet, tid, 512)
           return
        
        if opcode == 5:
            self.errorHandler(r_packet)
            return
      
        if opcode == 6:
            options = self.oackHandler(r_packet[2:], options)
            blksize = options["blksize"]
            tsize = options["tsize"]

            # ITS ONLY 0 IF THERE IS AN OPTION THAT WAS ACKNOLEDGED
            start = 0 if blksize != 512 or tsize != 0 else 1
            self.getFiles(start, filename, r_packet, tid, blksize)
        
    def set_dest(self, ip):
        if re.match(IPv4_PTRN, ip):
            self.destIP = ip
            print(f"[INF] Destination IP address set to {ip}")
        else:
            print(f"[ERR] Invalid IP address {ip}")

    def show_dest(self):
        print(f"[INF] Destination IP address is set to {self.destIP}")
    
    def close_connection(self):
        print(f"[INF] Closing the program.")
        self.running = False
    
    def help(self):
        print("Commands:")
        print("  set-dest [ip]                  set destination ip")
        print("  put [file] [options]           upload a file to the server")
        print("  get [file] [options]           download a file from the server")
        print("  show-dest                      show destination ip")
        print("  close                          close the program")
        print("  ?                              show this help message")
        print("")
        print("Options:")
        print(" -b [value]                      block size option")
        print(" -t                              transfer size option")

if __name__ == "__main__":
    client = Clientv3()
