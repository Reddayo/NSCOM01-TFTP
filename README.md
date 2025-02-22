# A simple TFTP client with options extension implementation
___
**Developed by:**
**Jusper Angelo M. Cesar**
**In accordance with the requirements of NSCOM01 Machine Project 1**
___
A simple TFTP client with options extension implementation

This client is designed to interact with a TFTP server to transfer files using the TFTP protocol.
It supports both reading and writing files over a UDP connection, and implements the TFTP 
options extension. It allows the client to negotiate block size and transfer size.

## Usage
Run the client:
```sh
python tftp_client.py
```

Once started, the client will enter interactive mode, where you can type commands:

### Commands
| Command      | Description |
|-------------|-------------|
| `put [file] [options]` | Upload a file to the TFTP server |
| `get [file] [options]` | Download a file from the TFTP server |
| `set-dest [IP]` | Set the TFTP server IP address |
| `show-dest` | Show the currently set TFTP server IP |
| `reset` | Reset the client settings |
| `?` | Show available commands |
| `close` | Exit the client |


## Error Handling

Implements a timeout mechanism of 5 seconds to "disconnect" client from a dead server.
Displays error messages for common issues such as missing files or unreachable servers.
Ignores duplicate ACK packets by processing only the first received ACK packet


## Test Cases

##### Server dies 

in the middle of a get operation
```
[INFO] Sent ACK for block 3101 to ('127.0.0.1', 51952).
[INFO] Processing block 3102.
[INFO] Sent ACK for block 3102 to ('127.0.0.1', 51952).
[INFO] Processing block 3103.
[INFO] Sent ACK for block 3103 to ('127.0.0.1', 51952).
[INFO] Processing block 3104.
[INFO] Sent ACK for block 3104 to ('127.0.0.1', 51952).
[INFO] Processing block 3105.
[INFO] Sent ACK for block 3105 to ('127.0.0.1', 51952).
[ERR] Failed to receive next DATA packet: timed out
>> 
```

in the middle of a put operation
```
[INFO] Received correct ACK for block 5024.
[INFO] Received correct ACK for block 5025.
[INFO] Received correct ACK for block 5026.
[INFO] Received correct ACK for block 5027.
[INFO] Received correct ACK for block 5028.
[ERR] Failed to receive next ACK packet
>> 
```

##### Server does not allow option negotiation:


Put -- Straight to ACK, like OACK did not exist
```
>> put chama_orig.jpg -o c.jpg -t -b 128
[INFO] File exists. Proceeding with transfer.
[INFO] Received b'\x00\x04\x00\x00' from ('127.0.0.1', 52158)...
[WARN] The options {'tsize': 3402976, 'blksize': 128} were discarded.
[INFO] Received correct ACK for block 1.
[INFO] Received correct ACK for block 2.
[INFO] Received correct ACK for block 3.
```
Get -- Straight to ACK, like OACK did not exist
```
>> get chama_orig.jpg -o c.jpg -t -b 128 
[INFO] Received b'\x00\x03\x00\x01\xff\xd...
[INFO] Processing block 1.
```

##### File does not exist in server
```
>> get a.txt 
[INFO] Received b'\x00\x05\x00\x01File not found\x00\x00' from ('127.0.0.1', 65258)...
[ERR] Code 1: File not found. Message: File not found
[INFO] Terminating process...
>>
```

##### Access Violation
```
>> put chama_orig.jpg -o ./dir/chama_orig.jpg
[INFO] File exists. Proceeding with transfer.
[INFO] Received b'\x00\x05\x00\x02Access violation\x00\x00' from ('127.0.0.1', 50535)...
[ERR] Code 2: Access violation. Message: Access violation
[INFO] Terminating process
>>

```

##### Succesful Transfer

Put
```
>> put chama_orig.jpg
...
...
...
[INFO] Received correct ACK for block 6646.
[INFO] Received correct ACK for block 6647.
[INFO] chama_orig.jpg has been sent succesfully.
>>
```

Get
```
>> get chama_orig.jpg
....
...
[INFO] Sent ACK for block 6646 to ('127.0.0.1', 65057).
[INFO] Processing block 6647.
[INFO] Sent ACK for block 6647 to ('127.0.0.1', 65057).
[INFO] File 'chama_orig.jpg' received successfully.
>>
```

Put with Options
```
>> put chama_orig.jpg -b 64000 -t
[INFO] File exists. Proceeding with transfer.
[INFO] Received b'\x00\x06blksize\x0016384\x00tsize\x003402976\x00' from ('127.0.0.1', 53245)...
[INFO] Received correct ACK for block 1.
...
...
...
[INFO] Received correct ACK for block 207.
[INFO] Received correct ACK for block 208.
[INFO] chama_orig.jpg has been sent succesfully.
>>
```

Get with options
```
>> get chama_orig.jpg  -t -b 64000  
[INFO] Received b'\x00\x06tsize\x003402976\x00blksize\x0016384\x00' from ('127.0.0.1', 52672)...
[INFO] Received OACK; sent ACK for block 0 to ('127.0.0.1', 52672).
[INFO] Received first DATA packet b'\x00\x03\x00\x01\xff\xd8\xff\xe...
...
...
...
[INFO] Sent ACK for block 208 to ('127.0.0.1', 52672).
[INFO] File 'chama_orig.jpg' received successfully.
>>
```


Put with file that is divisible by blksize
```
>> put s.txt -t    
[INFO] File exists. Proceeding with transfer.
[INFO] Received b'\x00\x06tsize\x00512\x00' from ('127.0.0.1', 62208)...
[INFO] Received correct ACK for block 1.
[INFO] Received correct ACK for block 2.
[INFO] s.txt has been sent succesfully.
>>
```

Get with file that is divisible by blksize

```
>> get s.txt -t
[INFO] Received b'\x00\x06tsize\x00512\x00' from ('127.0.0.1', 56724)...
[INFO] Received OACK; sent ACK for block 0 to ('127.0.0.1', 56724).
[INFO] Received first DATA packet b'\x00\x03\x00\x011234567\r\n1234567\r\n...
...
...
...
[INFO] Processing block 1.
[INFO] Sent ACK for block 1 to ('127.0.0.1', 56724).
[INFO] Processing block 2.
[INFO] Sent ACK for block 2 to ('127.0.0.1', 56724).
[INFO] File 's.txt' received successfully.
[INFO] File transfer complete.
>>
```