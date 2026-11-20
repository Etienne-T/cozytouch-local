import socket
import sys
with socket.create_connection(('127.0.0.1', 6666), timeout=10) as sock:
    sock.settimeout(120)
    for command in sys.argv[1:]:
        print('COMMAND:', command, flush=True)
        sock.sendall(command.encode() + b'\x1a')
        result = b''
        while b'\x1a' not in result:
            chunk = sock.recv(65536)
            if not chunk:
                raise RuntimeError('OpenOCD connection closed')
            result += chunk
        print(result.split(b'\x1a')[0].decode(errors='replace'), flush=True)
