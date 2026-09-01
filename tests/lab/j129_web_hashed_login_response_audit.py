#!/usr/bin/env python3
"""Audita de forma sanitizada la respuesta del login Web UI con hash del Avaya J129.

No imprime password, nonce, hash ni cookies. No cambia configuracion y no reinicia.
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
BOOT_PATH = "/cgi-bin/J100WebServer.cgi?Operation=0"
LOGIN_PATH = "/cgi-bin/J100WebServer.cgi?Operation=1"
MAX_BODY = 1024 * 1024

class SafeParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.tags = []
        self.texts = []
    def handle_starttag(self, tag, attrs):
        if tag not in self.tags:
            self.tags.append(tag)
    def handle_data(self, data):
        value = " ".join(data.split())
        if value:
            self.texts.append(value)

def read_response(opener, request):
    try:
        r = opener.open(request, timeout=8)
        try:
            return r.getcode(), r.headers.get("Content-Type", "no-publicado"), r.read(MAX_BODY)
        finally:
            r.close()
    except HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", "no-publicado") if exc.headers else "no-publicado", exc.read(MAX_BODY)

def cookie_value(jar, name):
    for cookie in jar:
        if cookie.name == name:
            return cookie.value
    return None

def safe_text(text):
    text = " ".join(text.split())
    text = re.sub(r"[A-Fa-f0-9]{32,}", "<hex-oculto>", text)
    text = re.sub(r"J100(?:nonce|sessionId)\s*[=:]\s*[^ ;'\"<]+", "J100token=<oculto>", text, flags=re.I)
    return text[:500]

def main():
    username = os.environ.get("J129_WEB_USER", "")
    password = os.environ.get("J129_WEB_PASSWORD", "")
    if not username or not password:
        print("ERROR: faltan credenciales web", file=sys.stderr)
        return 2

    print("=== J129 WEB HASHED LOGIN RESPONSE AUDIT ===")
    print("Telefono=%s" % PHONE_IP)
    print("Modo=respuesta-sanitizada")
    print("Acciones-prohibidas=change-password,restart,reboot,Operation=4")

    ctx = ssl._create_unverified_context()
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar), HTTPSHandler(context=ctx))
    base = "https://%s" % PHONE_IP

    try:
        status, _ctype, _body = read_response(opener, Request(base + BOOT_PATH, headers={"User-Agent":"Issabel-J129-Hashed-Login-Response-Audit/1.0"}))
    except (URLError, OSError) as exc:
        print("bootstrap=ERROR:%s" % exc.__class__.__name__)
        return 1
    nonce = cookie_value(jar, "J100nonce")
    session_id = cookie_value(jar, "J100sessionId")
    print("bootstrap-status=%s" % status)
    print("nonce-presente=%s" % int(bool(nonce)))
    print("session-presente=%s" % int(bool(session_id)))
    if not nonce or not session_id:
        return 1

    pass_hash = hashlib.sha256((password + nonce).encode("utf-8")).hexdigest().upper()
    data = urlencode({"uname": username, "psw": pass_hash}).encode("ascii")
    req = Request(base + LOGIN_PATH, data=data, headers={
        "User-Agent":"Issabel-J129-Hashed-Login-Response-Audit/1.0",
        "Content-Type":"application/x-www-form-urlencoded",
        "Cache-Control":"no-cache",
    })
    try:
        login_status, login_ctype, login_body = read_response(opener, req)
    except (URLError, OSError) as exc:
        print("login=ERROR:%s" % exc.__class__.__name__)
        return 1

    text = login_body.decode("iso-8859-1", "replace")
    parser = SafeParser()
    parser.feed(text)
    print("login-status=%s" % login_status)
    print("login-content-type=%s" % login_ctype)
    print("login-bytes=%s" % len(login_body))
    print("login-sha256=%s" % hashlib.sha256(login_body).hexdigest())
    print("html-tags=%s" % (",".join(parser.tags) if parser.tags else "ninguno"))
    fragments = [safe_text(x) for x in parser.texts if safe_text(x)]
    print("text-fragments=%s" % (" | ".join(fragments[:8]) if fragments else "ninguno"))
    low = text.lower()
    markers = []
    for marker in ("success", "invalid", "password", "login", "nonce", "session", "change", "failed", "error"):
        if marker in low:
            markers.append(marker)
    print("semantic-markers=%s" % (",".join(markers) if markers else "ninguno"))
    print("J129-WEB-HASHED-LOGIN-RESPONSE-AUDIT-PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())
