# A simple TFTP client with options extension implementation
# Written by Jusper Angelo M. Cesar
# In accordance with the requirements of NSCOM01 Machine Project 1

# This client is designed to interact with a TFTP server to transfer files using the TFTP protocol.
# It supports both reading and writing files over a UDP connection, and implements the TFTP 
# options extension. It allows the client to negotiate block size and transfer size.

import shutil
import socket
import struct
import os
import re


# begin issues
# issues read cant handle multiple data entries multiple times
# USE "reset" to clear backlogged packets 
# end issues 

# The first port of the TFTP Server
TFTP_SERVER_PORT = 69
# Default Block Size transfer
DEF_BLK_SIZE = 512
# Regex pattern for IPv4, used for input validation
IPv4_PTRN = r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]?|0)\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]?|0)$"
# TFTP Error codes, and meaning
ERR_CODES = {
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

class TFTPClient:
    # Initialize the fields used by TFTPClient and starts the loop
    def __init__(self):
        # the default destination ip address
        self.destIP =  "127.0.0.1"
        # creating the socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # setting a timeout of 5 seconds
        self.timeout = 5
        self.sock.settimeout(self.timeout)
        # Maximum amount of retries
        self.max_retries = 0
        # mapping the commands
        self.command_map = {
            "put": self.put,
            "get": self.get,
            "set-dest": self.setDest,
            "show-dest": self.showDest,
            "?": self.help,
            "close": self.closeProg,
            "reset": self.reset,
        }
        self.running = True
        self.start()
    
    # The loop
    def start(self):
        print("Welcome to the TFTP Client!")
        print("Client Version 4.0")
        print("Author: Jusper Angelo M. Cesar")
        print("")
        print("Default destination IP set as 127.0.0.1. Use 'set-dest' to configure.")
        print("Enter ? for commands.")
        while self.running:
            userinput = input(">> ").strip()
            # apparently it's not called a switch case in python
            self.switchCase(userinput)

    # Calls the commands, based on user input
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

    # Makes the request packet
    def requestMaker(self, opcode, filename, options: dict = None):
        
        if (opcode != 1) and (opcode != 2):
            raise ValueError("[ERR] Invalid opcode. Must be 1 (RRQ) or 2 (WRQ).")

        packet = opcode.to_bytes(2, "big") + filename.encode() + b"\x00" + b"octet" + b"\x00"

        for option, value in options.items():
            packet += option.encode() + b"\x00" + str(value).encode() + b"\x00"

        return packet
    

    # Handler for write and read commands
    def putgetHandler(self, command, args):

        filename = None
        output_filename = None
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
                    print(f"[ERR] Block size is not in range 8 to 65464: {blksize}")
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
            output_filename = os.path.basename(filename)
        
        self.command_map[command](filename, output_filename, options)

    # Send error packet to the server
    def sendErr(self, tid, code, message):
 
        errPacket = struct.pack("!HH", 5, code)  
        errPacket += message.encode("ascii") + b"\x00" 
        
        # Send the error packet to the server
        self.sock.sendto(errPacket, tid)  
        print(f"[ERR] Error packet sent. Code: {code}, Message: {message}")

    # Handles oack for both rrq and wrq
    def oackHandler(self, data, tid, options):
        # seen_options will be used to check if options has already been placed
        seen_options = set()
        acknowledged = False
        while data:
            try:
                name, data = data.split(b"\x00", 1)
                name = name.decode("ascii")

                if not data:
                    print("[ERR] Malformed OACK packet (missing value)")
                    self.sendErr(tid, 8, "Missing value.")
                    return None

                value, data = data.split(b"\x00", 1)
                try:
                    value_int = int(value.decode())
                except Exception as e:
                    print(f"[ERR] Invalid value for option {name}: {value}")
                    self.sendErr(tid, 8, "Invalid value for option.")
                    return None

                if name in seen_options:
                    print(f"[ERR] Duplicate option detected: {name}")
                    self.sendErr(tid, 8, "Duplicate option detected.")
                    return None
                
                if name not in options:
                    print(f"[ERR] Option is not in sent options: {name}")
                    self.sendErr(tid, 8, "Option is not in sent options.")
                    return None
                
                if name == "blksize":
                    if value_int <= options["blksize"]:
                        options[name] = value_int
                        acknowledged = True
                    else:
                        print(f"[ERR] Block size value exceeds the expected limit: {value_int} > {options['blksize']}")
                        self.sendErr(tid, 8, "Block size value exceeds the expected limit.")
                        return None
                elif name == "tsize":
                    total, used, free = shutil.disk_usage("/")
                    if value_int > free:
                        print(f"[ERR] File size exceeds available disk space: {value_int} > {free}")
                        self.sendErr(tid, 3, "File size exceeds available disk space.")
                        return None
                    else:
                        acknowledged = True

                seen_options.add(name)

            except Exception as e:
                print("[ERR] Malformed OACK packet")
                return None
        
        # Reset blk size back to default, if it was not acknowledged
        if "blksize" not in seen_options:
            options["blksize"] = DEF_BLK_SIZE
        
        return acknowledged, options
    
    def errHandler(self, error_packet):
        opcode = int.from_bytes(error_packet[0:2], "big")

        if opcode != 5:
            print("[ERR] Packet is not an error packet.")
            return

        code = int.from_bytes(error_packet[2:4], "big")
        msg = error_packet[4:].decode().strip("\x00")

        meaning = ERR_CODES.get(code, "Unknown error code")
        print(f"[ERR] Code {code}: {meaning}. Message: {msg}")
        print(f"[INFO] Terminating process...")
    

    def get(self, filename, output_filename, options):
        # Send the RRQ packet 
        if options.get("tsize"):
            options["tsize"] = 0
         # Client port is randomly selected by the operating system
        self.sock.sendto(self.requestMaker(1, filename, options), (self.destIP, TFTP_SERVER_PORT))
        
        # Receive OACK/DATA/ERROR packet
        try:
            r_packet, tid  = self.sock.recvfrom(DEF_BLK_SIZE + 4)
            print(f"[INFO] Received {r_packet} from {tid}...")
        except Exception as e:
            print(f"[ERR] {e}")
            return
        
        opcode = int.from_bytes(r_packet[0:2], "big")

        # DATA  - acknowledge of Read Request, but not the options;
        if opcode == 3:
            blksize = 512
            start = 1
            block_num = int.from_bytes(r_packet[2:4], "big")
            if block_num != 1:
                print(f"[ERR] Unexpected block number {block_num} in DATA packet; expected 1.")
                print(f"[ERR] Use 'reset' to clear backlogged packets")
                return
            
            start = 1
        # OACK - acknowledge of Read Request and the options;
        elif opcode == 6:
            ackbool, options = self.oackHandler(r_packet[2:], tid, options)
            if ackbool is None:
                return None
            blksize = options.get("blksize", DEF_BLK_SIZE)
            # If ackbool is True, start processing from block 0 (OACK requires an ACK).
            start = 0 if ackbool else 1

        # ERROR - the request has been denied.
        elif opcode == 5:
            self.errHandler(r_packet)
            return
        
        else:
            print(f"[ERR] Received unexpected opcode in RRQ, {opcode} not in (3, 5, 6)")
            return

        self.getFiles(start, output_filename, r_packet, tid, blksize)


    def getFiles(self, start, filename, r_packet, tid, blksize):
    
        last_block = start - 1

        try:
            with open(filename, "wb") as file:
                # Handle OACK if start == 0.
                if start == 0:
                    opcode = int.from_bytes(r_packet[0:2], "big")
                    if opcode == 6:
                        # Send ACK for block 0 per TFTP OACK handling.
                        ack_packet = struct.pack("!H", 4) + (0).to_bytes(2, "big")
                        self.sock.sendto(ack_packet, tid)
                        print(f"[INFO] Received OACK; sent ACK for block 0 to {tid}.")

                        # Wait for the first DATA packet (should be block 1).
                        try:
                            r_packet, tid = self.sock.recvfrom(blksize + 4)
                            print(f"[INFO] Received first DATA packet {r_packet} from {tid}.")
                        except Exception as e:
                            print(f"[ERR] Failed to receive first DATA packet after OACK: {e}")
                            return
                        # After OACK, we start processing at block 1.
                        last_block = 0
                    else:
                        print(f"[ERR] Expected OACK (opcode 6) but received opcode {opcode}; aborting.")
                        return

                # Process DATA packets.
                while True:
                    opcode = int.from_bytes(r_packet[0:2], "big")

                    if opcode == 5:
                        self.errHandler(r_packet)
                        return
                    elif opcode != 3:
                        print(f"[ERR] Unexpected opcode {opcode} received; expected DATA (3). Aborting.")
                        return

                    block_num = int.from_bytes(r_packet[2:4], "big")
                    print(f"[INFO] Processing block {block_num}.")

                    if block_num == last_block:
                        # Duplicate block detected; re-send the ACK.
                        ack_packet = struct.pack("!H", 4) + block_num.to_bytes(2, "big")
                        self.sock.sendto(ack_packet, tid)
                        print(f"[WARN] Duplicate block {block_num} received; re-sent ACK.")
                    else:
                        # Write new data and send ACK.
                        file.write(r_packet[4:])
                        last_block = block_num
                        ack_packet = struct.pack("!H", 4) + block_num.to_bytes(2, "big")
                        self.sock.sendto(ack_packet, tid)
                        print(f"[INFO] Sent ACK for block {block_num} to {tid}.")

                    # If the received data block is smaller than the negotiated block size,
                    # this signals the end of the file.
                    if len(r_packet) < blksize + 4:
                        print(f"[INFO] File '{filename}' received successfully.")
                        break

                    # Wait for the next DATA packet.
                    try:
                        r_packet, tid = self.sock.recvfrom(blksize + 4)
                    except Exception as e:
                        print(f"[ERR] Failed to receive next DATA packet: {e}")
                        return

            print("[INFO] File transfer complete.")
        except IOError as io_err:
            print(f"[ERR] Failed to write to file '{filename}': {io_err}")



    # Handles the sending of write operation to the TFTP Server
    def put(self, filename, output_filename, options):

        # Build the WRQ packet
        if not os.path.exists(filename):
            print(f"[ERR] File does not exist: {filename}")
            return
        
        print(f"[INFO] File exists. Proceeding with transfer.")

        if options.get("tsize"):
            options["tsize"] = os.path.getsize(filename)

        # Send the WRQ packet 
        self.sock.sendto(self.requestMaker(2, output_filename, options), (self.destIP, TFTP_SERVER_PORT))

        # Receive OACK/ACK/ERROR packet
        try:
            r_packet, tid  = self.sock.recvfrom(DEF_BLK_SIZE + 4)
            print(f"[INFO] Received {r_packet} from {tid}...")
        except Exception as e:
            print(f"[ERR] {e}")
            return
        
        # Check the opcode, CHECK FOR ERROR CODES
        opcode = int.from_bytes(r_packet[0:2], "big")
        
        # ACK   - acknowledge of Write Request, but not the options;
        if opcode == 4:
            blksize = 512
            if options:
                print(f"[WARN] The options {options} were discarded.")

        # ERROR - the request has been denied.
        elif opcode == 5:
            self.errHandler(r_packet)
            return
        
        # OACK  - acknowledge of Write Request and the options;
        elif opcode == 6:
            ackbool, options = self.oackHandler(r_packet[2:], tid, options)
            if ackbool is None:
                return None
            blksize = options.get("blksize", DEF_BLK_SIZE)

        else:
            print(f"[ERR] Received unexpected opcode in WRQ, {opcode} not in (4, 5, 6)")
            return

        # Start file transfer
        filesize = os.path.getsize(filename)
        block_num = 1
        with open(filename, "rb") as file:
            while chunk := file.read(blksize):
                data_packet = struct.pack("!H", 3) + block_num.to_bytes(2, "big") + chunk
                if not self.putFiles(data_packet, block_num, tid, blksize):
                    return
                block_num += 1

        if filesize % blksize == 0:
            empty_data_packet = struct.pack("!H", 3) + block_num.to_bytes(2, "big")
            if not self.putFiles(empty_data_packet, block_num, tid, blksize):
                return

        print(f"[INFO] {filename} has been sent succesfully.") 
    
    def putFiles(self, packet, expected_block_num, tid, blksize):
        retries = 0
        self.sock.sendto(packet, tid)
        while True:
            try:
                r_packet, addr = self.sock.recvfrom(blksize + 4)
            except socket.timeout:
                if self.max_retries > 0:
                    retries += 1
                    print(f"[WARN] Timeout, resending block {expected_block_num} (retry {retries}/{self.max_retries})...")
                    if retries >= self.max_retries:
                        print(f"[ERR] Max retries reached for block {expected_block_num}, aborting transfer.")
                        return False
                    self.sock.sendto(packet, tid)
                    continue
                else:
                    print(f"[WARN] Timeout reached, aborting transfer.")
                    return False
            except Exception as e:
                print(f"[ERR] {e}")
                return

            # Check for wrong TID, If so, send an error and ignore this packet.
            if addr != tid:
                print(f"[WARN] Received packet from unknown TID {addr}. Sending error and ignoring packet.")
                self.sendError(addr, 5, "Unknown transfer ID")
                continue

            opcode = int.from_bytes(r_packet[0:2], "big")
            if opcode == 5:
                # Received an error packet from the correct TID: abort.
                self.errHandler(r_packet)
                return False
            elif opcode == 4:
                ack_block = int.from_bytes(r_packet[2:4], "big")
                if ack_block == expected_block_num:
                    print(f"[INFO] Received correct ACK for block {expected_block_num}.")
                    return True
                elif ack_block < expected_block_num:
                    print(f"[WARN] Duplicate ACK {ack_block} received, ignoring...")
                    continue
                else:
                    print(f"[ERR] Out-of-order ACK {ack_block} received for block {expected_block_num}, aborting transfer.")
                    return False
            else:
                print(f"[ERR] Unexpected opcode {opcode} received, ignoring packet.")
                continue

    # Closes and reopens the socket, useful when there are backlogged packets 
    # from previous operations and is interferring with the current operation.
    def reset(self):
        try:
            # Close the socket if it's open
            if self.sock:
                self.sock.close()
                print("[INFO] Closed existing socket.")
        except Exception as e:
            print(f"[ERR] Error while closing socket: {e}")

        try:
            # Reopen the UDP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(self.timeout)
            print("[INFO] Socket has been reinitialized.")
        except Exception as e:
            print(f"[ERR] Failed to reinitialize socket: {e}")

    # Sets a new destination IP address that matches the IPv4 regex pattern
    def setDest(self, ip):
        if re.match(IPv4_PTRN, ip):
            self.destIP = ip
            print(f"[INFO] Destination IP address set to {ip}")
        else:
            print(f"[ERR] Invalid IP address {ip}")

    # Displays the destination IP address
    def showDest(self):
        print(f"[INFO] Destination IP address is set to {self.destIP}")
    
    # Closes the program, by closing the loop
    def closeProg(self):
        print(f"[INFO] Closing the program.")
        self.running = False

    # Shows information about the commands
    def help(self):
        print("Commands:")
        print("  put [file] [options]           upload a file to the server")
        print("  get [file] [options]           download a file from the server")
        print("  set-dest [ip]                  set destination ip")
        print("  show-dest                      show destination ip")
        print("  close                          close the program")
        print("  reset                          used for clearing backlogged packets")
        print("  ?                              show this help message")
        print("")
        print("Options:")
        print(" -b [value]                      add tftp block size option")
        print(" -t                              toggle tftp transfer size option")
        print(" -o [file]                       rename output file")

if __name__ == "__main__":
    client = TFTPClient()