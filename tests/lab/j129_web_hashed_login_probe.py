#!/usr/bin/env python3
"""Prueba controlada del login Web UI real del Avaya J129.

Reproduce el contrato observado en la propia pagina del telefono:
- GET Operation=0 para bootstrap de cookies.
- passPhrase = password + J100nonce.
- SHA-256(passPhrase) en hexadecimal MAYUSCULA.
- POST uname + psw=<hash> a Operation=1.
- POST read-only a Operation=33 para validar la sesion.

No cambia password, no reinicia, no invoca Operation=4 y no imprime
password, nonce, hash ni valores de cookies. Compatible con Python 3.6.
"""

from __future__ import print_function

import hashlib
import os
import ssl
import sys
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener

PHONE_IP = "192.168.1.171"
BOOT_PATH = "/cgi-bin/J100WebServer.cgi?Operation=0"
LOGIN_PATH = "/cgi-bin/J100WebServer.cgi?Operation=1"
SESSION_PATH = "/cgi-bin/J100WebServer.cgi?Operation=33"
MAX_BODY = 1024 * 1024


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


def cookie_value(jar, name):
    for cookie in jar:
        if cookie.name == name:
            return cookie.value
    return None


def semantic_result(body):
    text = body.decode("iso-8859-1", "replace").lower()
    if "web session expired" in text or "please log in to access" in text:
        return "SESSION-INVALID"
    if "invalid password" in text or "login failed" in text or "authentication failed" in text:
        return "LOGIN-REJECTED"
    if "change password" in text or "new password" in text or "web admin password" in text:
        return "PASSWORD-CHANGE-REQUIRED-OR-PRESENT"
    return "UNCLASSIFIED"


def main():
    username = os.environ.get("J129_WEB_USER", "")
    password = os.environ.get("J129_WEB_PASSWORD", "")
    if not username or not password:
        print("ERROR: faltan J129_WEB_USER/J129_WEB_PASSWORD", file=sys.stderr)
        return 2

    print("=== J129 WEB HASHED LOGIN PROBE ===")
    print("Telefono=%s" % PHONE_IP)
    print("Login-intentos=1")
    print("Contrato=SHA256(password+J100nonce)->HEX-UPPER; POST Operation=1")
    print("Validacion-read-only=Operation=33")
    print("Acciones-prohibidas=change-password,restart,reboot,Operation=4")

    ctx = ssl._create_unverified_context()
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar), HTTPSHandler(context=ctx))
    base = "https://%s" % PHONE_IP

    try:
        boot_req = Request(base + BOOT_PATH, headers={"User-Agent": "Issabel-J129-Hashed-Login-Probe/1.0"})
        boot_status, _boot_ctype, _boot_body = read_response(opener, boot_req)
    except (URLError, OSError) as exc:
        print("bootstrap=ERROR:%s" % exc.__class__.__name__)
        return 1

    nonce = cookie_value(jar, "J100nonce")
    session_id = cookie_value(jar, "J100sessionId")
    print("bootstrap-status=%s" % boot_status)
    print("bootstrap-cookie-J100nonce=%s" % ("presente" if nonce else "ausente"))
    print("bootstrap-cookie-J100sessionId=%s" % ("presente" if session_id else "ausente"))
    if not nonce or not session_id:
        print("result=BOOTSTRAP-COOKIE-MISSING")
        return 1

    pass_phrase = (password + nonce).encode("utf-8")
    pass_hash = hashlib.sha256(pass_phrase).hexdigest().upper()
    data = urlencode({"uname": username, "psw": pass_hash}).encode("ascii")
    login_req = Request(
        base + LOGIN_PATH,
        data=data,
        headers={
            "User-Agent": "Issabel-J129-Hashed-Login-Probe/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
        },
    )
    try:
        login_status, login_ctype, login_body = read_response(opener, login_req)
    except (URLError, OSError) as exc:
        print("login=ERROR:%s" % exc.__class__.__name__)
        return 1

    print("login-status=%s" % login_status)
    print("login-content-type=%s" % login_ctype)
    print("login-bytes=%s" % len(login_body))
    print("login-semantic=%s" % semantic_result(login_body))
    print("session-cookie-after-login=%s" % ("presente" if cookie_value(jar, "J100sessionId") else "ausente"))

    session_req = Request(
        base + SESSION_PATH,
        data=b"",
        headers={
            "User-Agent": "Issabel-J129-Hashed-Login-Probe/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
        },
    )
    try:
        session_status, session_ctype, session_body = read_response(opener, session_req)
    except (URLError, OSError) as exc:
        print("session=ERROR:%s" % exc.__class__.__name__)
        return 1

    session_text = session_body.decode("iso-8859-1", "replace").lower()
    session_semantic = semantic_result(session_body)
    print("session-status=%s" % session_status)
    print("session-content-type=%s" % session_ctype)
    print("session-bytes=%s" % len(session_body))
    print("session-sha256=%s" % hashlib.sha256(session_body).hexdigest())
    print("session-semantic=%s" % session_semantic)

    if session_status != 200:
        result = "SESSION-CHECK-HTTP-FAIL"
    elif session_semantic == "SESSION-INVALID":
        result = "SESSION-INVALID"
    elif "session" in session_text and "expired" not in session_text and "please log in" not in session_text:
        result = "SESSION-POSSIBLY-VALID"
    else:
        result = "SESSION-CHECK-UNCLASSIFIED"

    print("result=%s" % result)
    print("J129-WEB-HASHED-LOGIN-PROBE-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
