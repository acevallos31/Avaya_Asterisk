#!/usr/bin/env python3
"""Prueba controlada de un unico login Web UI al Avaya J129.

Realiza exactamente un POST de autenticacion usando las credenciales suministradas
por variables de entorno. No cambia password, no reinicia, no invoca Operation=4
y no imprime credenciales ni cookies. Compatible con Python 3.6.
"""

from __future__ import print_function

import os
import ssl
import sys
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener

PHONE_IP = "192.168.1.171"
LOGIN_PATH = "/cgi-bin/J100WebServer.cgi?Operation=0"
MAX_BODY = 1024 * 1024


class PageParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.title_parts = []
        self._in_title = False
        self.forms = []
        self.inputs = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "form":
            self.forms.append(((attrs.get("method") or "GET").upper(), attrs.get("action") or ""))
        elif tag == "input":
            self.inputs.append(((attrs.get("name") or "").strip(), (attrs.get("type") or "text").lower()))
        elif tag == "script" and attrs.get("src"):
            self.scripts.append(attrs.get("src"))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)

    @property
    def title(self):
        return " ".join(" ".join(self.title_parts).split())[:160]


def classify(body_text, parser):
    lower = body_text.lower()
    input_names = set(name.lower() for name, _kind in parser.inputs if name)
    markers = {
        "login_form": ("uname" in input_names and "psw" in input_names),
        "password_change": any(token in lower for token in (
            "change password", "new password", "confirm password", "password change",
            "force_web_admin_password", "web password", "changepassword"
        )),
        "authenticated_ui": any(token in lower for token in (
            "logout", "restart", "reboot", "system information", "device information"
        )) or any("main.js" in src.lower() for src in parser.scripts),
        "invalid_login": any(token in lower for token in (
            "invalid password", "invalid username", "login failed", "authentication failed",
            "incorrect password", "wrong password"
        )),
    }
    if markers["password_change"]:
        result = "PASSWORD-CHANGE-REQUIRED-OR-PRESENT"
    elif markers["authenticated_ui"] and not markers["login_form"]:
        result = "AUTHENTICATED"
    elif markers["invalid_login"]:
        result = "LOGIN-REJECTED"
    elif markers["login_form"]:
        result = "LOGIN-FORM-RETURNED"
    else:
        result = "UNCLASSIFIED"
    return result, markers


def main():
    username = os.environ.get("J129_WEB_USER", "")
    password = os.environ.get("J129_WEB_PASSWORD", "")
    if not username or not password:
        print("ERROR: faltan J129_WEB_USER/J129_WEB_PASSWORD", file=sys.stderr)
        return 2

    print("=== J129 WEB DEFAULT LOGIN PROBE ===")
    print("Telefono=%s" % PHONE_IP)
    print("Intentos=1")
    print("Acciones prohibidas=change-password,restart,reboot,Operation=4")

    ctx = ssl._create_unverified_context()
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar), HTTPSHandler(context=ctx))
    base = "https://%s" % PHONE_IP
    url = base + LOGIN_PATH

    # Bootstrap de sesion con GET publico.
    try:
        req = Request(url, headers={"User-Agent": "Issabel-J129-Login-Probe/1.0"})
        resp = opener.open(req, timeout=8)
        try:
            resp.read(MAX_BODY)
        finally:
            resp.close()
    except (HTTPError, URLError, OSError) as exc:
        print("bootstrap=ERROR:%s" % exc.__class__.__name__)
        return 1

    bootstrap_cookie_names = sorted(c.name for c in jar)
    print("bootstrap=OK")
    print("cookies-before-post=%s" % (",".join(bootstrap_cookie_names) if bootstrap_cookie_names else "ninguna"))

    data = urlencode({"uname": username, "psw": password}).encode("ascii")
    req = Request(
        url,
        data=data,
        headers={
            "User-Agent": "Issabel-J129-Login-Probe/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    try:
        resp = opener.open(req, timeout=8)
        try:
            status = resp.getcode()
            final_url = resp.geturl()
            body = resp.read(MAX_BODY)
            content_type = resp.headers.get("Content-Type", "no-publicado")
        finally:
            resp.close()
    except HTTPError as exc:
        status = exc.code
        final_url = exc.geturl()
        body = exc.read(MAX_BODY)
        content_type = exc.headers.get("Content-Type", "no-publicado") if exc.headers else "no-publicado"
    except (URLError, OSError) as exc:
        print("post=ERROR:%s" % exc.__class__.__name__)
        return 1

    text = body.decode("iso-8859-1", "replace")
    parser = PageParser()
    parser.feed(text)
    result, markers = classify(text, parser)

    print("post-status=%s" % status)
    print("content-type=%s" % content_type)
    print("bytes=%s" % len(body))
    print("title=%s" % (parser.title or "no-detectado"))
    print("final-path=%s" % (final_url.split(PHONE_IP, 1)[-1] if PHONE_IP in final_url else "no-local"))
    print("cookies-after-post=%s" % (",".join(sorted(c.name for c in jar)) if list(jar) else "ninguna"))
    print("marker-login-form=%s" % int(markers["login_form"]))
    print("marker-password-change=%s" % int(markers["password_change"]))
    print("marker-authenticated-ui=%s" % int(markers["authenticated_ui"]))
    print("marker-invalid-login=%s" % int(markers["invalid_login"]))
    print("result=%s" % result)

    # La prueba es observacional: cualquier respuesta HTTP valida se conserva como evidencia.
    print("J129-WEB-DEFAULT-LOGIN-PROBE-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
