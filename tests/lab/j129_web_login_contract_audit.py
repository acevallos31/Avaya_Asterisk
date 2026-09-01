#!/usr/bin/env python3
"""Audita read-only el contrato de login Web UI del Avaya J129.

Obtiene Operation=0 y los JavaScript locales referenciados para identificar
campos, onsubmit, nonce, hashing y transformaciones previas al POST.
No envia credenciales y no modifica el telefono. Compatible con Python 3.6.
"""
from __future__ import print_function

import hashlib
import re
import ssl
import sys
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPSHandler, Request, build_opener

PHONE_IP = "192.168.1.171"
LOGIN_PATH = "/cgi-bin/J100WebServer.cgi?Operation=0"
MAX_BODY = 1024 * 1024

class Parser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.forms = []
        self.inputs = []
        self.scripts = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self.forms.append({
                "method": (a.get("method") or "GET").upper(),
                "action": a.get("action") or "",
                "onsubmit": a.get("onsubmit") or "",
                "id": a.get("id") or "",
                "name": a.get("name") or "",
            })
        elif tag == "input":
            self.inputs.append({
                "name": a.get("name") or "",
                "type": a.get("type") or "text",
                "id": a.get("id") or "",
                "value_present": int("value" in a and bool(a.get("value"))),
            })
        elif tag == "script" and a.get("src"):
            self.scripts.append(a.get("src"))

def fetch(opener, url):
    req = Request(url, headers={"User-Agent":"Issabel-J129-Login-Contract-Audit/1.0"})
    try:
        r = opener.open(req, timeout=8)
        try:
            return r.getcode(), r.headers.get("Content-Type", ""), r.read(MAX_BODY)
        finally:
            r.close()
    except HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", "") if exc.headers else "", exc.read(MAX_BODY)

def safe_contexts(text):
    pats = [r"onsubmit", r"uname", r"psw", r"nonce", r"J100nonce", r"hash", r"sha", r"md5", r"password", r"Operation=0", r"submit\("]
    out = []
    lower = text.lower()
    for p in pats:
        for m in re.finditer(p.lower(), lower):
            s = max(0, m.start()-180); e = min(len(text), m.end()+260)
            frag = " ".join(text[s:e].split())
            frag = re.sub(r'(?i)(value\s*=\s*["\']).*?(["\'])', r'\1<redacted>\2', frag)
            if frag not in out:
                out.append(frag[:520])
            if len(out) >= 20:
                return out
    return out

def main():
    print("=== J129 WEB LOGIN CONTRACT AUDIT ===")
    print("Telefono=%s" % PHONE_IP)
    print("Modo=solo-lectura")
    print("Credenciales-enviadas=0")
    print("Acciones-prohibidas=login,change-password,restart,reboot,Operation=4")
    ctx = ssl._create_unverified_context()
    opener = build_opener(HTTPSHandler(context=ctx))
    base = "https://%s" % PHONE_IP
    try:
        status, ctype, body = fetch(opener, base + LOGIN_PATH)
    except (URLError, OSError) as exc:
        print("login-page=ERROR:%s" % exc.__class__.__name__)
        return 1
    text = body.decode("iso-8859-1", "replace")
    p = Parser(); p.feed(text)
    print("page-status=%s" % status)
    print("page-content-type=%s" % ctype)
    print("page-bytes=%s" % len(body))
    print("page-sha256=%s" % hashlib.sha256(body).hexdigest())
    for i, f in enumerate(p.forms, 1):
        print("form-%02d=method:%s action:%s id:%s name:%s onsubmit:%s" % (i, f['method'], f['action'] or '-', f['id'] or '-', f['name'] or '-', f['onsubmit'] or '-'))
    for i, inp in enumerate(p.inputs, 1):
        print("input-%02d=name:%s type:%s id:%s value-present:%s" % (i, inp['name'] or '-', inp['type'], inp['id'] or '-', inp['value_present']))
    print("scripts=%s" % (",".join(p.scripts) if p.scripts else "ninguno"))
    contexts = safe_contexts(text)
    for i, frag in enumerate(contexts, 1):
        print("page-context-%02d=%s" % (i, frag))
    for src in p.scripts:
        full = urljoin(base + LOGIN_PATH, src)
        parsed = urlparse(full)
        if parsed.hostname != PHONE_IP:
            print("script-skip-external=%s" % src)
            continue
        try:
            sstatus, sctype, sbody = fetch(opener, full)
        except (URLError, OSError) as exc:
            print("script-error=%s:%s" % (src, exc.__class__.__name__))
            continue
        stext = sbody.decode("iso-8859-1", "replace")
        print("script=%s status:%s bytes:%s sha256:%s" % (src, sstatus, len(sbody), hashlib.sha256(sbody).hexdigest()))
        for i, frag in enumerate(safe_contexts(stext), 1):
            print("script-context-%s-%02d=%s" % (re.sub(r'[^A-Za-z0-9_.-]+','_',src), i, frag))
    print("J129-WEB-LOGIN-CONTRACT-AUDIT-PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())
