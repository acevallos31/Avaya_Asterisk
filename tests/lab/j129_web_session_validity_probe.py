#!/usr/bin/env python3
"""Valida de forma no destructiva una sesion Web UI del Avaya J129.

Flujo:
1. GET publico de Operation=0 para obtener cookies de bootstrap.
2. Un unico POST de login con credenciales de variables de entorno.
3. POST read-only a Operation=33, documentado por el propio main.js del telefono
   como comprobacion de timeout/validez de sesion.

No cambia password, no reinicia, no invoca Operation=4 y no imprime
credenciales ni valores de cookies. Compatible con Python 3.6.
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
MAX_BODY = 1024 * 1024


class LoginFormParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.inputs = []

    def handle_starttag(self, tag, attrs):
        if tag != "input":
            return
        data = dict(attrs)
        self.inputs.append((data.get("name") or "").strip().lower())

    @property
    def has_login_form(self):
        names = set(self.inputs)
        return "uname" in names and "psw" in names


def read_response(opener, request):
    try:
        response = opener.open(request, timeout=8)
        try:
            return (
                response.getcode(),
                response.headers.get("Content-Type", "no-publicado"),
                response.read(MAX_BODY),
            )
        finally:
            response.close()
    except HTTPError as exc:
        return (
            exc.code,
            exc.headers.get("Content-Type", "no-publicado") if exc.headers else "no-publicado",
            exc.read(MAX_BODY),
        )


def safe_token(body):
    text = body.decode("iso-8859-1", "replace").strip()
    if len(text) <= 80 and re.match(r"^[A-Za-z0-9_.:+-]+$", text or ""):
        return text
    return "oculto-no-escalar"


def main():
    username = os.environ.get("J129_WEB_USER", "")
    password = os.environ.get("J129_WEB_PASSWORD", "")
    if not username or not password:
        print("ERROR: faltan J129_WEB_USER/J129_WEB_PASSWORD", file=sys.stderr)
        return 2

    print("=== J129 WEB SESSION VALIDITY PROBE ===")
    print("Telefono=%s" % PHONE_IP)
    print("Login-intentos=1")
    print("Operacion-validacion=33")
    print("Acciones-prohibidas=change-password,restart,reboot,Operation=4")

    ctx = ssl._create_unverified_context()
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar), HTTPSHandler(context=ctx))
    base = "https://%s" % PHONE_IP

    # Bootstrap publico.
    try:
        req = Request(base + LOGIN_PATH, headers={"User-Agent": "Issabel-J129-Session-Probe/1.0"})
        status, _ctype, _body = read_response(opener, req)
    except (URLError, OSError) as exc:
        print("bootstrap=ERROR:%s" % exc.__class__.__name__)
        return 1

    print("bootstrap-status=%s" % status)
    print("bootstrap-cookies=%s" % (",".join(sorted(c.name for c in jar)) if list(jar) else "ninguna"))

    # Un unico POST de login.
    data = urlencode({"uname": username, "psw": password}).encode("ascii")
    login_req = Request(
        base + LOGIN_PATH,
        data=data,
        headers={
            "User-Agent": "Issabel-J129-Session-Probe/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
        },
    )
    try:
        login_status, login_ctype, login_body = read_response(opener, login_req)
    except (URLError, OSError) as exc:
        print("login=ERROR:%s" % exc.__class__.__name__)
        return 1

    parser = LoginFormParser()
    parser.feed(login_body.decode("iso-8859-1", "replace"))
    print("login-status=%s" % login_status)
    print("login-content-type=%s" % login_ctype)
    print("login-bytes=%s" % len(login_body))
    print("login-form-returned=%s" % int(parser.has_login_form))
    print("session-cookies=%s" % (",".join(sorted(c.name for c in jar)) if list(jar) else "ninguna"))

    # Operation=33: main.js la identifica como comprobacion de timeout de sesion.
    session_req = Request(
        base + SESSION_PATH,
        data=b"",
        headers={
            "User-Agent": "Issabel-J129-Session-Probe/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
        },
    )
    try:
        session_status, session_ctype, session_body = read_response(opener, session_req)
    except (URLError, OSError) as exc:
        print("session-check=ERROR:%s" % exc.__class__.__name__)
        return 1

    token = safe_token(session_body)
    lower = session_body.decode("iso-8859-1", "replace").strip().lower()
    print("session-status=%s" % session_status)
    print("session-content-type=%s" % session_ctype)
    print("session-bytes=%s" % len(session_body))
    print("session-sha256=%s" % hashlib.sha256(session_body).hexdigest())
    print("session-token=%s" % token)

    if session_status != 200:
        result = "SESSION-CHECK-HTTP-FAIL"
    elif lower in ("true", "1", "valid", "ok", "success"):
        result = "SESSION-VALID"
    elif lower in ("false", "0", "invalid", "expired", "timeout"):
        result = "SESSION-INVALID"
    elif parser.has_login_form and len(session_body) > 512:
        result = "LOGIN-LIKELY-NOT-ESTABLISHED"
    else:
        result = "SESSION-CHECK-UNCLASSIFIED"

    print("result=%s" % result)
    print("J129-WEB-SESSION-VALIDITY-PROBE-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
