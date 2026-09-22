#!/usr/bin/env python3
from __future__ import print_function

import io
import sys

MARKER = 'CEIBA-GRANDSTREAM-PROD-V2-GXP16XX'
ANCHOR = "        if sModel != None: self._saveModel(sModel)\n\n    def updateLocalConfig(self):\n"

INSERT = r'''        if sModel == None:
            sModel = self._probeModelFromAsterisk()

        if sModel != None: self._saveModel(sModel)

    def _probeModelFromAsterisk(self):
        """Read-only fallback for modern Grandstream phones.

        When the phone is already registered, Asterisk knows both the peer IP
        and its Useragent. This lets a clean Endpoint Configurator installation
        identify GRP26xx models without authenticating to or writing the phone.
        """
        ami = None
        try:
            ami = self._amipool.get()
            peer = None
            for raw in ami.Command('sip show peers'):
                line = raw.replace('Output: ', '').strip()
                parts = line.split()
                if len(parts) < 2 or parts[1] != self._ip:
                    continue
                peer = parts[0].split('/')[0]
                if peer:
                    break

            if not peer:
                return None

            useragent = None
            for raw in ami.Command('sip show peer %s' % peer):
                line = raw.replace('Output: ', '').strip()
                if line.lower().startswith('useragent') and ':' in line:
                    useragent = line.split(':', 1)[1].strip()
                    break

            if not useragent:
                return None

            upper = useragent.upper()
            model = None
            if 'GRP2601' in upper:
                model = 'GRP2601P'
            elif 'GRP2602G' in upper:
                model = 'GRP2602G'
            elif 'GXP1625' in upper:
                model = 'GXP1625'

            if model is not None:
                logging.info(
                    'Endpoint %s@%s model detected from Asterisk peer %s Useragent %s -> %s' %
                    (self._vendorname, self._ip, peer, useragent, model))
                return model
        except Exception as e:
            logging.info(
                'Endpoint %s@%s Asterisk Useragent model probe unavailable - %s' %
                (self._vendorname, self._ip, str(e)))
        finally:
            if ami is not None:
                self._amipool.put(ami)

        return None

    def updateLocalConfig(self):
'''

def main():
    if len(sys.argv) != 3:
        print('usage: grandstream-clean-bootstrap-patch.py INPUT OUTPUT', file=sys.stderr)
        return 2

    src, dst = sys.argv[1], sys.argv[2]
    with io.open(src, 'r', encoding='utf-8') as fh:
        content = fh.read()

    if MARKER not in content:
        print('ERROR: input is not Ceiba Grandstream V2 runtime', file=sys.stderr)
        return 3
    if '_probeModelFromAsterisk' in content:
        print('ERROR: clean-bootstrap fallback already present', file=sys.stderr)
        return 4
    if ANCHOR not in content:
        print('ERROR: probeModel anchor not found', file=sys.stderr)
        return 5

    content = content.replace(ANCHOR, INSERT, 1)

    with io.open(dst, 'w', encoding='utf-8') as fh:
        fh.write(content)

    return 0

if __name__ == '__main__':
    sys.exit(main())
