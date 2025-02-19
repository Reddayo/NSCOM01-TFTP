# Written by Jusper Angelo M. Cesar

# A TFTP server with option extension


# issues error code 5 terminates the transfer
# issues read cant handle multiple data entries
# no more issues 

import shutil
import socket as soc
import os
import struct 
import re

# First server port
TFTP_SERVER_PORT = 69
# Client port is chosen completely at random
# pattern for ipv4
IPv4_PTRN = r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]?|0)\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]?|0)$"
# Error Codes and meaning
ERROR_CODES = {
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


DEFAULT_BLK_SIZE = 512


class Clientv4:


    def __init__(self):
        self.destIP =  "127.0.0.1"
        self.sock = soc.socket(soc.AF_INET, soc.SOCK_DGRAM)
        self.sock.settimeout(5)
        self.timeout = 5
        self.running = True
        self.command_map = {
            "put": self.put,
            "get": self.get,
            "set-dest": self.setDest,
            "show-dest": self.showDest,
            "?": self.help,
            "close": self.closeConnection,
            "reset": self.reset,
        }
        
        self.start()

    def start(self):
        print("Welcome to the TFTP Client!")
        print("Client Version 4.0")
        print("Author: Jusper Angelo M. Cesar")
        print("")
        print("Default destination IP set as 127.0.0.1. Use 'set-dest' to configure.")
        print("Enter ? for commands.")
        while self.running:
            user_input = input(">> ").strip()
            self.switchCase(user_input)

    def reset(self):
        try:
            # Close the existing socket if it's open.
            if self.sock:
                self.sock.close()
                print("[INF] Closed existing socket.")
        except Exception as e:
            print(f"[ERR] Error while closing socket: {e}")

        try:
            # Recreate the UDP socket.
            self.sock = soc.socket(soc.AF_INET, soc.SOCK_DGRAM)
            # Optionally, set a timeout or other socket options.
            self.sock.settimeout(self.timeout)
            print("[INF] Socket has been reinitialized.")
        except Exception as e:
            print(f"[ERR] Failed to reinitialize socket: {e}")
    def switchCase(self, input):
        tokens = input.split()

        if not tokens:
            print("[ERR] No command entered.")
            return
        
        command = tokens[0].lower()
        args = tokens[1:]

        if command not in self.command_map:
            print("[ERR] Invalid command. Use '?' for help.")
            return

        if command in {"put", "get"}:
            self.putgetHandler(command, args)
        elif command == "set-dest":
            if len(args) != 1:
                print("[ERR] Invalid Syntax: set-dest [ip]")
                return
            self.command_map[command](args[0])
        else:
            self.command_map[command]()

    def putgetHandler(self, command, args):

        filename = None
        output_filename = None
        # Default options, would be changed based on args
        options = {}
        i = 0
        while i < len(args):
            arg = args[i]

            if arg == "-b":
                if "blksize" in options:
                    print("[ERR] Duplicate blksize flag detected.")
                    return
                if i + 1 >= len(args) or not args[i + 1].isdigit():
                    print("[ERR] Missing or invalid blksize value.")
                    return
                
                blksize = int(args[i + 1])
                
                if blksize <  8 or blksize > 65464:
                    print(f"[ERR] Block size is not in range [8:65464]: {blksize}")
                    return
                
                options["blksize"] = blksize
                i += 1

            elif arg == "-t":
                if "tsize" in options:
                    print("[ERR] Duplicate tsize flag detected.")
                    return
                options["tsize"] = True

            elif arg == "-o":
                if output_filename:
                    print("[ERR] Duplicate output flag detected.")

                if i + 1 >= len(args):
                    print("[ERR] Missing or invalid output name.")
                    return
                
                output_filename = args[i+1]
                i += 1

            elif filename is None:
                filename = arg

            else:
                print(f"[ERR] Unknown option: {arg}")
                return

            i += 1

        if filename is None:
            print(f"[ERR] Invalid Syntax: {command} [filename] [options]")
            return
        
        # default values

        if output_filename is None:
            output_filename = filename

        self.command_map[command](filename, output_filename, options)

    def getFiles(self, start, filename, r_packet, tid, blksize):
       
        last_block = start - 1  

        with open(filename, "wb") as file:
            # --- Handle OACK (opcode 6) when expected ---
            if start == 0:
                opcode = struct.unpack("!H", r_packet[0:2])[0]
                if opcode == 6:
                    # Received OACK; send ACK for block 0.
                    ack_packet = struct.pack("!H", 4) + (0).to_bytes(2, "big")
                    self.sock.sendto(ack_packet, tid)
                    print(f"[INF] Received OACK (opcode 6), sent ACK for block 0 to {tid}.")
                    # Now wait for the first DATA packet (which should be block 1)
                    try:
                        r_packet, tid  = self.sock.recvfrom(blksize + 4)
                        print(f"[INFI] Received {r_packet} from {tid}...")
                    except Exception as e:
                        print(f"[ERR] Failed to receive data: {e}")
                        return
                    start = 1
                    last_block = 0
                else:
                    print(f"[ERR] Expected OACK (opcode 6) but received opcode {opcode}, aborting...")
                    return

            # --- Main loop to process DATA packets (opcode 3) ---
            while True:
                opcode = struct.unpack("!H", r_packet[0:2])[0]

                # Handle error packet.
                if opcode == 5:
                    self.errHandler(r_packet)
                    return
                # If it's not a DATA packet, it's unexpected.
                elif opcode != 3:
                    print(f"[ERR] Unexpected opcode {opcode} received, aborting...")
                    return
                
                # Extract block number (bytes 2-4).
                block_num = int.from_bytes(r_packet[2:4], "big")
                print(f"This is inside getfiles: {block_num}")
                if block_num == last_block:
                    # Duplicate block received; ignore without resending ACK.
                    print(f"[WRN] Duplicate block {block_num} received; ignoring duplicate.")
                else:
                    # New block received: write data and send ACK.
                    file.write(r_packet[4:])
                    last_block = block_num
                    ack_packet = struct.pack("!H", 4) + block_num.to_bytes(2, "big")
                    self.sock.sendto(ack_packet, tid)
                    print(f"[INF] Sent ACK for block {block_num} to {tid}.")

                # If the received data portion is smaller than the negotiated block size,
                # then this is the final packet.
                if len(r_packet) < blksize + 4:
                    print(f"[INF] File '{filename}' received successfully.")
                    break

                # Wait for the next data packet.
                try:
                    r_packet, tid  = self.sock.recvfrom(blksize + 4)
                    
                except Exception as e:
                    print(f"[ERR] Failed to receive data: {e}")
                    return

        print(f"[INF] File transfer complete.")

    def requestMaker(self, opcode, filename, options: dict = None):
        
        if (opcode != 1) and (opcode != 2):
            raise ValueError("[ERR] Invalid opcode. Must be 1 (RRQ) or 2 (WRQ).")

        packet = opcode.to_bytes(2, "big") + filename.encode() + b"\x00" + b"octet" + b"\x00"

        if options:
            packet += self.buildOptions(options)

        print(f"[INF] Sending {packet} to ({self.destIP}, {TFTP_SERVER_PORT})...")
        return packet
    
    def buildOptions(self, options):
  
        packet = b""

        for option, value in options.items():
            packet += option.encode() + b"\x00" + str(value).encode() + b"\x00"

        return packet


    def errHandler(self, error_packet):
        opcode = int.from_bytes(error_packet[0:2], "big")

        if opcode != 5:
            print("[ERR] Packet is not an error packet.")
            return

        code = int.from_bytes(error_packet[2:4], "big")
        msg = error_packet[4:].decode().strip("\x00")

        # I know that 5 should not terminate the process
        meaning = ERROR_CODES.get(code, "Unknown error code")
        print(f"[ERR] Code {code}: {meaning}. Message: {msg}")
        print(f"[INF] Terminating process...")

    # Changes the value of options based the received oack packet
    def oackHandler(self, data, options):
        # seen_options will be used to check if options has already been placed
        seen_options = set()
        acknowledged = False
        while data:
            try:
                name, data = data.split(b"\x00", 1)
                name = name.decode("ascii")

                if not data:
                    print("[ERR] Malformed OACK packet (missing value)")
                    self.sendErr(8, "Missing value.")
                    return None

                value, data = data.split(b"\x00", 1)
                try:
                    value_int = int(value.decode())
                except Exception as e:
                    print(f"[ERR] Invalid value for option {name}: {value}")
                    self.sendErr(8, "Invalid value for option.")
                    return None

                if name in seen_options:
                    print(f"[ERR] Duplicate option detected: {name}")
                    self.sendErr(8, "Duplicate option detected.")
                    return None
                
                if name not in options:
                    print(f"[ERR] Option is not in sent options: {name}")
                    self.sendErr(8, "Option is not in sent options.")
                    return None
                
                if name == "blksize":
                    if value_int <= options["blksize"]:
                        options[name] = value_int
                        acknowledged = True
                    else:
                        print(f"[ERR] Block size value exceeds the expected limit: {value_int} > {options['blksize']}")
                        self.sendErr(8, "Block size value exceeds the expected limit.")
                        return None
                elif name == "tsize":
                    total, used, free = shutil.disk_usage("/")
                    if value_int > free:
                        print(f"[ERR] File size exceeds available disk space: {value_int} > {free}")
                        self.sendErr(3, "File size exceeds available disk space.")
                        return None
                    else:
                        acknowledged = True

                seen_options.add(name)

            except Exception as e:
                print("[ERR] Malformed OACK packet")
                return None
        
        # Remove options that has necessary value that weren't acknowledged
        if "blksize" not in seen_options:
            options["blksize"] = 512
        
        return acknowledged, options
    
    # Create the error packet
    def sendErr(self, code, message):
 
        errPacket = struct.pack("!HH", 5, code)  
        errPacket += message.encode("ascii") + b"\x00" 
        
        # Send the error packet to the client
        self.sock.sendto(errPacket, self.destIP)  
        print(f"[SEND ERR] Error packet sent. Code: {code}, Message: {message}")

    def put(self, filename, output_filename, options):
        # Build the WRQ packet

        if not os.path.exists(filename):
            print(f"[ERR] File does not exist: {filename}")
            return
        print(f"[INF] File exists. Proceeding with transfer.")

        if "tsize" in options:
            if options["tsize"]:
                options["tsize"] = os.path.getsize(filename)

        # Send the WRQ packet 
        self.sock.sendto(self.requestMaker(2, output_filename, options), (self.destIP, TFTP_SERVER_PORT))
        
        

        # Receive OACK/ACK/ERROR packet
        try:
            r_packet, tid  = self.sock.recvfrom(DEFAULT_BLK_SIZE + 4)
            print(f"[INFO] Received {r_packet} from {tid}...")
        except Exception as e:
            print(f"[ERR] Failed to receive data: {e}")
            return
        
        # Check the opcode, CHECK FOR ERROR CODES
        opcode = int.from_bytes(r_packet[0:2], "big")
        

        # ACK   - acknowledge of Write Request, but not the options;
        if opcode == 4:
            blksize = 512
            if options:
                print(f"[WRN] The options {options} were discarded.")

        # ERROR - the request has been denied.
        if opcode == 5:
            self.errHandler(r_packet)
            return
        
        # OACK  - acknowledge of Write Request and the options;
        if opcode == 6:
            ackbool, options = self.oackHandler(r_packet[2:], options)
            if ackbool is None:
                return None
            blksize = options["blksize"]

        with open(filename, "rb") as file:
            filesize = os.path.getsize(filename)
            i = 1 
            max_retries = 5
            retries = 0
            while chunk := file.read(blksize):
                pck = struct.pack("!H", 3) + i.to_bytes(2, "big") + chunk
                self.sock.sendto(pck, tid)
                while True:
                    try:
                        h, a = self.sock.recvfrom(blksize + 4)
                        print(f"[INFI] Received {h} from {a}...")
                        print(f"[INF] {blksize}")
                        print(f"[INF] {len(chunk)}")
                        print(f"[INF] {filesize}")
                    except soc.timeout:
                        print(f"[WARN] Timeout, resending block {i}...")
                        self.sock.sendto(pck, tid)
                        retries += 1

                        if retries == max_retries:
                            print(f"[ERR] Max retries has been reached, terminating process...")
                            return None
                        continue
                    
                    ope = int.from_bytes(h[0:2], "big")
                    ack_block = int.from_bytes(h[2:4], "big")

                    if ope == 5:
                        self.errHandler(h)
                        return

                    if ope == 4:
                        if ack_block == i:
                            print(f"[INF] Received correct ACK for block {i}")
                            retries = 0
                            break 
                        elif ack_block < i:  
                            print(f"[WARN] Duplicate ACK {ack_block}, ignoring...")
                            continue 
                        else:
                            print(f"[ERR] Out-of-order ACK {ack_block}, aborting...")
                            return
                i += 1

            if filesize % blksize == 0:
                empty_packet = struct.pack("!H", 3) + (i).to_bytes(2, "big")
                self.sock.sendto(empty_packet, tid)
                print(f"[INF] Empty packet sent for block {i}.")
                try:
                    h, a = self.sock.recvfrom(blksize + 4)
                    print(f"[INFI] Received {h} from {a}...")
                    print(f"[INF] {blksize}")
                    print(f"[INF] {len(chunk)}")
                    print(f"[INF] {filesize}")
                except soc.timeout:
                    print(f"[WARN] Timeout, resending block {i}...")
                    retries += 1

                    if retries == max_retries:
                        print(f"[ERR] Max retries has been reached, terminating process...")
                        return None

                ope = int.from_bytes(h[0:2], "big")
                ack_block = int.from_bytes(h[2:4], "big")

                if ope == 5:
                    self.errHandler(h)
                    return

                if ope == 4:
                    if ack_block == i:
                        print(f"[INF] Received correct ACK for block {i}")
                    else:
                        print(f"[WARN] Duplicate/old ACK {ack_block}, resending block {i}...")

        print(f"[INF] {filename} has been sent succesfully.") 

            
    def get(self, filename, output_filename, options):

        # Send the RRQ packet 
        if "tsize" in options:
            if options["tsize"]:
                options["tsize"] = 0
         # Client port is randomly selected by the operating system
        self.sock.sendto(self.requestMaker(1, filename, options), (self.destIP, TFTP_SERVER_PORT))
        
        # Receive OACK/DATA/ERROR packet
        try:
            r_packet, tid  = self.sock.recvfrom(DEFAULT_BLK_SIZE + 4)
            print(f"[INF] Received {r_packet} from {tid}...")
        except Exception as e:
            print(f"[ERR] Failed to receive data: {e}")
            return
        
        opcode = int.from_bytes(r_packet[0:2], "big")

        # DATA  - acknowledge of Read Request, but not the options;
        if opcode == 3:
            blksize = 512
            start = 1
            block_num = int.from_bytes(r_packet[2:4], "big")
            if(block_num != 1):
                print("Received packet is different")
                return 

        # OACK - acknowledge of Read Request and the options;
        elif opcode == 6:
            ackbool, options = self.oackHandler(r_packet[2:], options)
            if ackbool is None:
                return None
            blksize = options["blksize"]
            # ITS ONLY 0 IF THERE IS AN OPTION THAT WAS ACKNOwLEDGED
            start = 0 if ackbool else 1

        # ERROR - the request has been denied.
        elif opcode == 5:
            self.errHandler(r_packet)
            return
        else:
            print(f"[ERR] Received invalid packet in RRQ, {opcode} not in (3, 5, 6)")
            return

        self.getFiles(start, output_filename, r_packet, tid, blksize)


    def setDest(self, ip):
        if re.match(IPv4_PTRN, ip):
            self.destIP = ip
            print(f"[INF] Destination IP address set to {ip}")
        else:
            print(f"[ERR] Invalid IP address {ip}")

    def showDest(self):
        print(f"[INF] Destination IP address is set to {self.destIP}")
    
    def closeConnection(self):
        print(f"[INF] Closing the program.")
        self.running = False
    
    def help(self):
        print("Commands:")
        print("  put [file] [options]           upload a file to the server")
        print("  get [file] [options]           download a file from the server")
        print("  set-dest [ip]                  set destination ip")
        print("  show-dest                      show destination ip")
        print("  close                          close the program")
        print("  ?                              show this help message")
        print("")
        print("Options:")
        print(" -b [value]                      add tftp block size option")
        print(" -t                              toggle tftp transfer size option")
        print(" -o [file]                       rename output file")


if __name__ == "__main__":
    client = Clientv4()
