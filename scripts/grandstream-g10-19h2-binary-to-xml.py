#!/usr/bin/env python3
import os, struct, urllib.parse, xml.etree.ElementTree as ET, hashlib

SRC = '/tftpboot/cfgc074ade86609'
DST = '/tftpboot/cfgc074ade86609.xml'
REPORT = os.environ.get('REPORT_PATH', '/tmp/g10-19h2.txt')
EXPECTED_MAC = 'c074ade86609'
EXPECTED_EXT = '202'
EXPECTED_PBX = '192.168.1.10'

lines=[]
def log(k,v): lines.append(f'{k}={v}')
log('scope','CONTROLLED_CFG_XML_GENERATION_FROM_ISSABEL_BINARY')
log('phone_write','NO_DIRECT_PHONE_WRITE')
log('pbx_live_provisioning_file_write','XML_CFG_ONLY')
log('db_write','NO')
log('factory_reset','NO')
log('cfg_payload_logged','NO')
log('sip_secret_logged','NO')

try:
    data=open(SRC,'rb').read()
    log('binary_cfg_state','PRESENT')
    log('binary_cfg_size',str(len(data)))
    log('binary_cfg_sha256',hashlib.sha256(data).hexdigest())
    if len(data) < 16:
        raise RuntimeError('CFG_TOO_SHORT')
    length, checksum = struct.unpack('>LH', data[:6])
    mac = data[6:12].hex()
    sep_ok = data[12:16] == b'\r\n\r\n'
    if mac != EXPECTED_MAC:
        raise RuntimeError('MAC_HEADER_MISMATCH')
    if not sep_ok:
        raise RuntimeError('LEGACY_SEPARATOR_MISSING')
    raw = data[16:]
    if raw.endswith(b'\x00'):
        raw = raw[:-1]
    text = raw.decode('utf-8')
    pairs = urllib.parse.parse_qsl(text, keep_blank_values=True)
    params = {k:v for k,v in pairs if k != 'gnkey'}
    log('decoded_parameter_count',str(len(params)))
    log('header_mac_match','YES')
    log('legacy_separator_match','YES')
    log('p35_target_202','YES' if params.get('P35') == EXPECTED_EXT else 'NO')
    log('p36_target_202','YES' if params.get('P36') == EXPECTED_EXT else 'NO')
    log('p34_secret_present','YES' if bool(params.get('P34')) else 'NO')
    log('p47_target_pbx','YES' if params.get('P47') == EXPECTED_PBX else 'NO')
    log('p270_target_ashly','YES' if 'ashly' in params.get('P270','').lower() else 'NO')
    if params.get('P35') != EXPECTED_EXT or params.get('P36') != EXPECTED_EXT or not params.get('P34') or params.get('P47') != EXPECTED_PBX:
        raise RuntimeError('BINARY_CFG_NOT_SAFE_FOR_202_XML')

    root=ET.Element('gs_provision', {'version':'1'})
    ET.SubElement(root,'mac').text=EXPECTED_MAC
    cfg=ET.SubElement(root,'config', {'version':'1'})
    for key in sorted(params, key=lambda x: (int(x[1:]) if x.startswith('P') and x[1:].isdigit() else 999999, x)):
        if key.startswith('P') and key[1:].isdigit():
            ET.SubElement(cfg,key).text=params[key]
    tree=ET.ElementTree(root)
    tmp=DST+'.tmp'
    tree.write(tmp, encoding='UTF-8', xml_declaration=True)
    os.chmod(tmp,0o644)
    os.replace(tmp,DST)
    xml_data=open(DST,'rb').read()
    log('xml_cfg_state','PRESENT')
    log('xml_cfg_size',str(len(xml_data)))
    log('xml_cfg_sha256',hashlib.sha256(xml_data).hexdigest())
    log('diagnostic','XML_CFG_GENERATED_FROM_ISSABEL_BINARY_202')
    log('next_activity','G10-19H3_TRIGGER_TFTP_PROV_AND_VERIFY_202')
except Exception as e:
    log('diagnostic','ERROR')
    log('error_class',str(e).replace(' ','_')[:120])
finally:
    log('G10-19H2-COMPLETE','YES')
    with open(REPORT,'w',encoding='utf-8') as f:
        f.write('\n'.join(lines)+'\n')
    os.chmod(REPORT,0o600)
    print('\n'.join(lines))
