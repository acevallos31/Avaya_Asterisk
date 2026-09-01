#!/usr/bin/env python3
"""Audita de forma sanitizada la respuesta de Operation=33 del Avaya J129.

Hace un unico login y luego consulta Operation=33. No cambia configuracion,
no reinicia y no imprime credenciales, cookies ni posibles tokens de sesion.
Compatible con Python 3.6.
"""
from __future__ import print_function

import hashlib
import os
import re
import ssl
import sys
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener

PHONE_IP = "192.168.1.171"
LOGIN_PATH = "/cgi-bin/J100WebServer.cgi?Operation=0"
SESSION_PATH = "/cgi-bin/J100WebServer.cgi?Operation=33"
MAX_BODY = 4096

class SanitizingParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.tags = []
        self.texts = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag.lower())
    def handle_data(self, data):
        text = " ".join(data.split())
        if text:
            self.texts.append(text)

def read_response(opener, request):
    try:
        r = opener.open(request, timeout=8)
        try:
            return r.getcode(), r.headers.get("Content-Type", "no-publicado"), r.read(MAX_BODY)
        finally:
            r.close()
    except HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", "no-publicado") if exc.headers else "no-publicado", exc.read(MAX_BODY)

def sanitize_text(text):
    # Nunca publicar valores largos o parecidos a tokens/ids de sesion.
    text = re.sub(r"[A-Fa-f0-9]{16,}", "<HEX-REDACTED>", text)
    text = re.sub(r"[A-Za-z0-9_\-+/=]{24,}", "<TOKEN-REDACTED>", text)
    text = re.sub(r"(?i)(J100sessionId|J100nonce)\s*[=:]\s*[^\s<>&;]+", r"\1=<REDACTED>", text)
    return text[:300]

def main():
    user = os.environ.get("J129_WEB_USER", "")
    password = os.environ.get("J129_WEB_PASSWORD", "")
    if not user or not password:
        print("ERROR: faltan credenciales por entorno", file=sys.stderr)
        return 2

    print("=== J129 WEB SESSION RESPONSE AUDIT ===")
    print("Telefono=%s" % PHONE_IP)
    print("Modo=solo-lectura")
    print("Login-intentos=1")
    print("Operacion=33")
    print("Acciones-prohibidas=change-password,restart,reboot,Operation=4")

    ctx = ssl._create_unverified_context()
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar), HTTPSHandler(context=ctx))
    base = "https://%s" % PHONE_IP

    try:
        s, _c, _b = read_response(opener, Request(base + LOGIN_PATH, headers={"User-Agent":"Issabel-J129-Session-Response-Audit/1.0"}))
        print("bootstrap-status=%s" % s)
        data = urlencode({"uname": user, "psw": password}).encode("ascii")
        s, _c, b = read_response(opener, Request(base + LOGIN_PATH, data=data, headers={"User-Agent":"Issabel-J129-Session-Response-Audit/1.0","Content-Type":"application/x-www-form-urlencoded","Cache-Control":"no-cache"}))
        print("login-status=%s" % s)
        print("login-bytes=%s" % len(b))

        req = Request(base + SESSION_PATH, data=b"", headers={"User-Agent":"Issabel-J129-Session-Response-Audit/1.0","Content-Type":"application/x-www-form-urlencoded","Cache-Control":"no-cache"})
        status, ctype, body = read_response(opener, req)
    except (URLError, OSError) as exc:
        print("ERROR=%s" % exc.__class__.__name__)
        return 1

    text = body.decode("iso-8859-1", "replace")
    parser = SanitizingParser()
    parser.feed(text)

    print("session-status=%s" % status)
    print("session-content-type=%s" % ctype)
    print("session-bytes=%s" % len(body))
    print("session-sha256=%s" % hashlib.sha256(body).hexdigest())
    print("html-tags=%s" % (",".join(sorted(set(parser.tags))) if parser.tags else "ninguna"))
    safe_texts = [sanitize_text(t) for t in parser.texts]
    safe_texts = [t for t in safe_texts if t and "<TOKEN-REDACTED>" not in t]
    print("text-fragments=%s" % (" | ".join(safe_texts[:10]) if safe_texts else "ninguno-publicable"))

    lower = text.lower()
    markers = []
    for marker in ("login", "logout", "timeout", "session", "invalid", "valid", "success", "error", "password", "main"):
        if marker in lower:
            markers.append(marker)
    print("semantic-markers=%s" % (",".join(markers) if markers else "ninguno"))
    print("J129-WEB-SESSION-RESPONSE-AUDIT-PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())
