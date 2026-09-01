#!/usr/bin/env python3
"""Auditoria read-only del formulario de login del Web UI Avaya J129.

Solo realiza GET contra la ruta publica de login. No envia credenciales, cookies
ni formularios. No imprime valores de inputs ni el HTML completo. Compatible
con Python 3.6.
"""

from __future__ import print_function

import hashlib
import ssl
import sys
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


PHONE_IP = "192.168.1.171"
LOGIN_PATH = "/cgi-bin/J100WebServer.cgi?Operation=0"
MAX_BODY = 1024 * 1024


class LoginParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.forms = []
        self.inputs = []
        self.links = []
        self.scripts = []
        self.title_parts = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "form":
            self.forms.append({
                "method": (attrs.get("method") or "GET").upper(),
                "action": attrs.get("action") or "",
            })
        elif tag == "input":
            self.inputs.append({
                "name": attrs.get("name") or "",
                "type": (attrs.get("type") or "text").lower(),
            })
        elif tag == "a" and attrs.get("href"):
            self.links.append(attrs.get("href"))
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
        return " ".join(" ".join(self.title_parts).split())[:200]


def fetch(url):
    req = Request(url, headers={"User-Agent": "Issabel-J129-ReadOnly-Audit/1.0"})
    context = None
    if url.startswith("https://"):
        context = ssl._create_unverified_context()
    response = urlopen(req, timeout=8, context=context)
    try:
        body = response.read(MAX_BODY)
        return response.getcode(), response.headers, body
    finally:
        response.close()


def same_origin_path(base_url, value):
    if not value:
        return ""
    target = urljoin(base_url, value)
    parsed = urlparse(target)
    base = urlparse(base_url)
    if parsed.hostname != base.hostname or parsed.scheme not in ("http", "https"):
        return "externo"
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    return path


def audit_scheme(scheme):
    base_url = "%s://%s" % (scheme, PHONE_IP)
    url = base_url + LOGIN_PATH
    print("=== %s LOGIN AUDIT ===" % scheme.upper())
    try:
        status, headers, body = fetch(url)
    except (HTTPError, URLError, OSError) as exc:
        print("result=ERROR:%s" % exc.__class__.__name__)
        return

    parser = LoginParser()
    parser.feed(body.decode("iso-8859-1", "replace"))

    print("status=%s" % status)
    print("server=%s" % headers.get("Server", "no-publicado"))
    print("content-type=%s" % headers.get("Content-Type", "no-publicado"))
    print("bytes=%s" % len(body))
    print("sha256=%s" % hashlib.sha256(body).hexdigest())
    print("title=%s" % (parser.title or "no-detectado"))

    print("forms=%s" % len(parser.forms))
    for idx, form in enumerate(parser.forms[:10], 1):
        print(
            "form-%02d=method:%s action:%s"
            % (idx, form["method"], same_origin_path(url, form["action"]) or "misma-ruta")
        )

    safe_inputs = []
    for item in parser.inputs:
        name = item["name"].strip()
        input_type = item["type"].strip()
        if not name:
            continue
        safe_inputs.append((name, input_type))

    print("inputs=%s" % len(safe_inputs))
    for idx, item in enumerate(safe_inputs[:30], 1):
        print("input-%02d=name:%s type:%s" % (idx, item[0], item[1]))

    refs = []
    for value in parser.links + parser.scripts:
        path = same_origin_path(url, value)
        if path and path != "externo" and path not in refs:
            refs.append(path)
    print("same-origin-resources=%s" % len(refs))
    for idx, path in enumerate(refs[:30], 1):
        print("resource-%02d=%s" % (idx, path))

    lower = body.decode("iso-8859-1", "replace").lower()
    markers = []
    for token in ("login", "password", "username", "admin", "restart", "reboot", "logout", "session", "csrf"):
        if token in lower:
            markers.append(token)
    print("markers=%s" % (",".join(markers) if markers else "ninguno"))


def main():
    print("=== J129 WEB LOGIN AUDIT (SOLO LECTURA) ===")
    print("Telefono=%s" % PHONE_IP)
    print("Ruta=%s" % LOGIN_PATH)
    print("Metodo=GET solamente; sin credenciales, cookies ni POST")
    audit_scheme("http")
    audit_scheme("https")
    print("J129-WEB-LOGIN-AUDIT-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
