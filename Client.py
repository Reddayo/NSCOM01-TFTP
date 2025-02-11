import socket as s
import os
import struct as st
import re

TFTP_Port = 69
IPv4_PTRN = r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]?|0)\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]?|0)$"




    # RRQ

    # WRQ

    # Data

    # Ack

    # Error

    # OptionAck



# Packet Builder Code - This should take in the opcode, 


class PacketBuilder:
    # No options for mode.... 
    def build(opcode, filename):
        packet = st.pack("!H", opcode) + b"%b\x00octet\x00" % filename.encode("ascii")
        return packet

    def buildData(block, data):
        packet = st.pack("!H", 3) + data
        return packet
    
    def buildAck(block):
        packet = st.pack("!H", 4) + block
        return packet

    def buildErr(errorCode, errorMsg):
        packet = st.pack("!H", 5) + errorCode + errorMsg + st.pack("!H", 5)
        return packet



# Error Builder Code - This should take in the opcode















class Client:
    def __init__(self):
        self.sock = s.socket(s.AF_INET, s.SOCK_DGRAM)
        self.start()
        self.destIP = "127.0.0.1"
        self.destPort = 69
        self.startPort = None
        

    def sendReq(self, opcode, filename):
        print("I think Im sending stuff rn")


        if not os.path.exists(filename):
            print(f"Error: File '{filename}' does not exist.")
            return
        
        packet = st.pack("!H", opcode)
        packet += filename.encode("ascii")
        packet += "\x00".encode()
        packet += "octet".encode("ascii")
        packet += "\x00".encode()
        print(packet)
        self.sock.sendto( packet, (self.destIP, TFTP_Port))
        self.sock.settimeout(5)
        try:
            h, a = self.sock.recvfrom(512)
        except Exception as e:
            print(f"Error receiving data: {e}")
            return

        i = 1
        with open(filename, "rb") as file:
            while chunk := file.read(512):
                pck = st.pack("!H", 3)
                
                pck += i.to_bytes(2, byteorder="big")
                pck += chunk
                self.sock.sendto(pck, a)
                h, a = self.sock.recvfrom(512)
                print(f"Received ACK for block {i}")
                print("Server Response:", h, a)
                i += 1
    
    def defReq(self, filename):
        print("I think Im getting stuff rn")

        
        packet = st.pack("!H", 1)
        packet += filename.encode("ascii")
        packet += "\x00".encode()
        packet += "octet".encode("ascii")
        packet += "\x00".encode()
        print(packet)
        self.sock.sendto( packet, (self.destIP, TFTP_Port))
        self.sock.settimeout(5)
        
        
        with open(filename, "wb") as file:
            while True:
                b, a =  self.sock.recvfrom(516)
                print("Server: ", b[0:4], a)
                opcode = st.unpack("!H", b[0:2])[0]

                if opcode == 5:
                    print("Received TFTP error packet")
                    break

                packet = None
                packet = st.pack("!H", 4) + b[2:4]
                self.sock.sendto(packet, a)

                file.write(b[4:])

                if len(b) < 516:
                    print(f"{filename} has been received")
                    break


        

        

    def start(self):
        print("idk how to make a goddamn Client")
        while self.running:
            user_input = input(">>").strip()
            self.switchCase(user_input)
        
        
    def connect(self, input):
        
        print(f"Connecting to {input}")
        
        if re.match(IPv4_PTRN, input):
            self.destIP = input
        else:
            print(f"Invalid IP address")


    def switchCase(self, input):
        
        command = input.split()[0]

        match command:
            case "connect":
                if(len(input.split()) == 2):
                    self.connect(input.split()[1])
                else:
                    print("Invalid Syntax Error: connect [ip]")
            case "/leave":
                print("call leave function")
            case "/close":
                print("call close function")
            case "/?":
                self.help()
            case "put":
                self.sendReq(2, "chama.jpg")
            case "get":
                self.defReq("chama.jpg")
            case _:
                print("Invalid command.")
            
            
        
    

    def help(self):
        print("Available commands:")
        print("  connect [ip]        - Connect to the server")
        print("  put [filename]      - Upload a file to the server")
        print("  get [filename]      - Download a file from the server")
        print("  /leave              - Disconnect from the server")
        print("  /?                  - Show this help message")
        print("  /close              - close the program")

if __name__ == "__main__":
     client = Client()
