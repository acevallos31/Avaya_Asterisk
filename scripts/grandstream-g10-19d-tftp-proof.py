#!/usr/bin/env python3
import hashlib
import os
import socket
import struct
import sys

report, source = sys.argv[1], sys.argv[2]
server = ('127.0.0.1', 69)
name = os.path.basename(source).encode()
req = struct.pack('!H', 1) + name + b'\0octet\0'
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(3)
s.sendto(req, server)
data = bytearray()
expected = 1
status = 'FAILED'
try:
    while True:
        pkt, addr = s.recvfrom(2048)
        op = struct.unpack('!H', pkt[:2])[0]
        if op == 5 or op != 3:
            break
        block = struct.unpack('!H', pkt[2:4])[0]
        if block != expected:
            break
        chunk = pkt[4:]
        data.extend(chunk)
        s.sendto(struct.pack('!HH', 4, block), addr)
        if len(chunk) < 512:
            status = 'SUCCESS'
            break
        expected = (expected + 1) & 0xffff
except Exception:
    pass
src = open(source, 'rb').read()
with open(report, 'a') as f:
    f.write('tftp_rrq=%s\n' % status)
    if status == 'SUCCESS':
        f.write('tftp_received_size=%d\n' % len(data))
        f.write('tftp_sha_match=%s\n' % ('YES' if hashlib.sha256(data).digest() == hashlib.sha256(src).digest() else 'NO'))
