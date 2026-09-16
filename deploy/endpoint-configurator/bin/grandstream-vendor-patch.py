#!/usr/bin/env python3
import pathlib
import sys

MARKER = 'CEIBA-GRANDSTREAM-PROD-V1'

if len(sys.argv) != 3:
    raise SystemExit('usage: vendor-patch.py SOURCE DEST')
src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])
text = src.read_text(encoding='utf-8')
if MARKER in text:
    dst.write_text(text, encoding='utf-8')
    raise SystemExit(0)

anchor = "import http.client\n"
if text.count(anchor) != 1:
    raise SystemExit('http.client import anchor mismatch')
text = text.replace(anchor, anchor + "import hashlib\nimport subprocess\n", 1)

old_parser = """    def _parseBotchedJSONResponse(self, response):\n        body = response.read().decode('utf-8')\n        logging.info(body)\n        jsonvars = json.loads(body)\n        return jsonvars\n"""
new_parser = """    def _parseBotchedJSONResponse(self, response):\n        body = response.read().decode('utf-8')\n        jsonvars = json.loads(body)\n        return jsonvars\n"""
if text.count(old_parser) != 1:
    raise SystemExit('JSON parser anchor mismatch')
text = text.replace(old_parser, new_parser, 1)

static_anchor = "    def _enableStaticProvisioning(self, vars):\n\n"
bridge = f"""    def _loadCredentialVaultPassword(self):\n        # {MARKER}: secret remains only in the root process and pipe.\n        cli = '/usr/local/libexec/issabel-endpoint-credential-vault'\n        if not os.path.isfile(cli):\n            return False\n        try:\n            env = dict(os.environ)\n            env['ENDPOINT_CREDENTIAL_ALLOW_EMIT'] = '1'\n            proc = subprocess.run(\n                [cli, 'emit-pending', self._mac],\n                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,\n                timeout=5, check=False, env=env)\n            if proc.returncode != 0:\n                return False\n            password = proc.stdout.decode('utf-8')\n            if not password or len(password) > 128 or '\\n' in password or '\\r' in password:\n                return False\n            self._http_password = password\n            return True\n        except Exception:\n            return False\n\n"""
if text.count(static_anchor) != 1:
    raise SystemExit('static provisioning anchor mismatch')
text = text.replace(static_anchor, bridge + static_anchor, 1)
route = f"""        # {MARKER}: GRP26xx never falls back to the legacy GXP contract.\n        self._loadCredentialVaultPassword()\n        if self._model and str(self._model).upper().startswith('GRP26'):\n            return self._enableStaticProvisioning_GRP26xx(vars)\n\n"""
text = text.replace(static_anchor, static_anchor + route, 1)

method_anchor = "    def _enableStaticProvisioning_GXP140x(self, vars):\n"
grp_methods = f"""    def _loginGRP26xx(self, conn, headers):\n        # {MARKER}: nonce challenge; cleartext password is never transmitted.\n        conn.request('GET', '/', headers=headers)\n        root = conn.getresponse()\n        root.read()\n        cookies = []\n        for name, value in root.getheaders():\n            if name.lower() == 'set-cookie':\n                pair = value.split(';', 1)[0].strip()\n                if pair:\n                    cookies.append(pair)\n        if cookies:\n            headers['Cookie'] = '; '.join(cookies)\n        access = urlencode({{'access': hashlib.sha256(self._http_username.encode('utf-8')).hexdigest()}})\n        conn.request('POST', '/cgi-bin/access', body=access, headers=headers)\n        response = conn.getresponse()\n        reply = json.loads(response.read().decode('utf-8'))\n        nonce = reply.get('body', '')\n        if response.status != 200 or reply.get('response') != 'success' or not isinstance(nonce, str) or not nonce:\n            return None\n        digest = hashlib.sha256((self._http_password + nonce).encode('utf-8')).hexdigest()\n        body = urlencode({{'username': self._http_username, 'password': digest}})\n        conn.request('POST', '/cgi-bin/dologin', body=body, headers=headers)\n        response = conn.getresponse()\n        reply = json.loads(response.read().decode('utf-8'))\n        payload = reply.get('body')\n        sid = payload.get('sid', '') if isinstance(payload, dict) else (payload if isinstance(payload, str) else '')\n        if response.status != 200 or reply.get('response') != 'success' or not sid:\n            return None\n        for name, value in response.getheaders():\n            if name.lower() == 'set-cookie':\n                pair = value.split(';', 1)[0].strip()\n                if pair and not pair.lower().startswith('session-identity='):\n                    cookies.append(pair)\n        cookies.append('session-identity=' + sid)\n        headers['Cookie'] = '; '.join(cookies)\n        return sid\n\n    def _enableStaticProvisioning_GRP26xx(self, vars):\n        try:\n            conn = http.client.HTTPConnection(self._ip)\n            headers = {{'Content-Type': 'application/x-www-form-urlencoded', 'Accept': '*/*',\n                       'Host': self._ip, 'Referer': 'http://%s/' % self._ip}}\n            sid = self._loginGRP26xx(conn, headers)\n            if not sid:\n                logging.error('Endpoint %s@%s GRP26xx challenge login failed' % (self._vendorname, self._ip))\n                return False\n            pvalues = {{}}\n            for key, value in vars.items():\n                key = str(key)\n                pvalues[key[1:] if key.startswith('P') else key] = value\n            headers['Content-Type'] = 'application/json'\n            conn.request('PUT', '/cgi-bin/config_update', body=json.dumps({{'alias': {{}}, 'pvalue': pvalues}}), headers=headers)\n            response = conn.getresponse()\n            reply = json.loads(response.read().decode('utf-8'))\n            if response.status != 200 or reply.get('response') != 'success':\n                logging.error('Endpoint %s@%s GRP26xx rejected config update' % (self._vendorname, self._ip))\n                return False\n            return True\n        except Exception as exc:\n            logging.error('Endpoint %s@%s GRP26xx provisioning failed - %s' % (self._vendorname, self._ip, str(exc)))\n            return False\n\n"""
if text.count(method_anchor) != 1:
    raise SystemExit('GXP140x method anchor mismatch')
text = text.replace(method_anchor, grp_methods + method_anchor, 1)

old_login = "            payload = urlencode({'password': self._http_password})"
new_login = """            payload = urlencode({\n                'username': self._http_username,\n                'password': self._http_password,\n            })"""
if text.count(old_login) != 1:
    raise SystemExit('GXP login anchor mismatch')
text = text.replace(old_login, new_login, 1)

text = text.replace(
    "logging.error('jsonvars vacio %s@%s GXP140x - vars rejected by interface - %s - %s - %s' %\n                              (self._vendorname, self._ip, urlencode(vars), 'N/A', sid))",
    "logging.error('Endpoint %s@%s GXP140x - vars rejected by interface' % (self._vendorname, self._ip))")
text = text.replace(
    "logging.error('Endpoint %s@%s GXP140x - vars rejected by interface - %s - %s - %s' %\n                              (self._vendorname, self._ip, urlencode(vars), jsonvars['body'], sid))",
    "logging.error('Endpoint %s@%s GXP140x - vars rejected by interface' % (self._vendorname, self._ip))")
text = text.replace("str(e), self._ssh_username, self._ssh_password", "str(e), self._ssh_username, '***'")

start = text.index("    def _rebootbyhttp(self):\n")
end = text.index("    def _hashTableGrandstreamConfig(self):\n", start)
legacy = text[start:end]
legacy_body = legacy[len("    def _rebootbyhttp(self):\n"):]
new_reboot = f"""    def _rebootbyhttp(self):\n        self._loadCredentialVaultPassword()\n        if self._model and str(self._model).upper().startswith('GRP26'):\n            try:\n                conn = http.client.HTTPConnection(self._ip)\n                headers = {{'Content-Type': 'application/x-www-form-urlencoded', 'Accept': '*/*',\n                           'Host': self._ip, 'Referer': 'http://%s/' % self._ip}}\n                sid = self._loginGRP26xx(conn, headers)\n                if not sid:\n                    return False\n                url = '/cgi-bin/api-sys_operation?' + urlencode({{'request': 'REBOOT', 'sid': sid}})\n                conn.request('GET', url, headers=headers)\n                response = conn.getresponse()\n                reply = json.loads(response.read().decode('utf-8'))\n                return response.status == 200 and reply.get('response') == 'success'\n            except Exception as exc:\n                logging.error('Endpoint %s@%s GRP26xx reboot failed - %s' % (self._vendorname, self._ip, str(exc)))\n                return False\n\n""" + legacy_body
text = text[:start] + new_reboot + text[end:]

dst.write_text(text, encoding='utf-8')
