#!/usr/bin/env python3
import hashlib
import socket
import struct
import sys

SERVER = ('192.168.1.10', 69)
FILENAME = b'cfgc074ade86609'
EXPECTED_SIZE = 586
EXPECTED_SHA256 = 'caed018769c28c67e2e0f8a039257a021401552dbbe549e077cfce61a50e90e8'

report = sys.argv[1] if len(sys.argv) > 1 else 'g10-19d3-network-tftp-proof.txt'

def out(line):
    print(line)
    with open(report, 'a', encoding='utf-8') as fh:
        fh.write(line + '\n')

open(report, 'w').close()
out('scope=NETWORK_READ_ONLY_PROOF')
out('target=PBX_LAB_TFTP')
out('phone_write=NO')
out('pbx_config_write=NO')
out('firewall_change=NO')

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(4)
req = struct.pack('!H', 1) + FILENAME + b'\0octet\0'
sock.sendto(req, SERVER)
data = bytearray()
expected_block = 1
status = 'FAILED'
error_code = 'NONE'
try:
    while True:
        pkt, addr = sock.recvfrom(2048)
        if len(pkt) < 4:
            error_code = 'SHORT_PACKET'
            break
        opcode = struct.unpack('!H', pkt[:2])[0]
        if opcode == 5:
            error_code = 'TFTP_ERROR'
            break
        if opcode != 3:
            error_code = 'UNEXPECTED_OPCODE'
            break
        block = struct.unpack('!H', pkt[2:4])[0]
        if block != expected_block:
            error_code = 'UNEXPECTED_BLOCK'
            break
        chunk = pkt[4:]
        data.extend(chunk)
        sock.sendto(struct.pack('!HH', 4, block), addr)
        if len(chunk) < 512:
            status = 'SUCCESS'
            break
        expected_block = (expected_block + 1) & 0xffff
except socket.timeout:
    error_code = 'TIMEOUT'
finally:
    sock.close()

sha = hashlib.sha256(data).hexdigest() if status == 'SUCCESS' else 'NOT_COMPUTED'
out('tftp_network_rrq=' + status)
out('tftp_error=' + error_code)
out('tftp_received_size=' + str(len(data)))
out('tftp_size_match=' + ('YES' if status == 'SUCCESS' and len(data) == EXPECTED_SIZE else 'NO'))
out('tftp_sha_match=' + ('YES' if status == 'SUCCESS' and sha == EXPECTED_SHA256 else 'NO'))
if status == 'SUCCESS' and len(data) == EXPECTED_SIZE and sha == EXPECTED_SHA256:
    out('diagnostic=TFTP_NETWORK_READY_AND_CFG_PROVEN')
    out('next_activity=G10-19E_PROVISIONING_STATE_PREFLIGHT')
else:
    out('diagnostic=TFTP_NETWORK_PROOF_FAILED')
    out('next_activity=G10-19D4_SERVER_BIND_DIAGNOSTIC')
out('G10-19D3-COMPLETE')
