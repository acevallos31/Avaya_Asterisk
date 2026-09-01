#!/usr/bin/env python3
"""Auditoria read-only del bootstrap de sesion Web UI Avaya J129.

Solo realiza GET al login y a main.js. No envia credenciales, cookies ni POST.
Los valores de cookies nunca se imprimen; solo nombre y atributos publicos.
Compatible con Python 3.6.
"""

from __future__ import print_function

import hashlib
import re
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PHONE_IP = "192.168.1.171"
LOGIN_PATH = "/cgi-bin/J100WebServer.cgi?Operation=0"
JS_PATH = "/main.js"
MAX_BODY = 1024 * 1024


def fetch(url):
    req = Request(url, headers={"User-Agent": "Issabel-J129-ReadOnly-Audit/1.0"})
    context = ssl._create_unverified_context() if url.startswith("https://") else None
    resp = urlopen(req, timeout=8, context=context)
    try:
        return resp.getcode(), resp.headers, resp.read(MAX_BODY)
    finally:
        resp.close()


def cookie_metadata(headers):
    values = headers.get_all("Set-Cookie") or []
    result = []
    for raw in values:
        parts = [p.strip() for p in raw.split(";") if p.strip()]
        if not parts:
            continue
        first = parts[0]
        name = first.split("=", 1)[0].strip() if "=" in first else first.strip()
        attrs = []
        for part in parts[1:]:
            key = part.split("=", 1)[0].strip().lower()
            if key:
                attrs.append(key)
        result.append((name or "sin-nombre", sorted(set(attrs))))
    return result


def snippets(text, token, radius=260, max_items=4):
    out = []
    low = text.lower()
    needle = token.lower()
    start = 0
    while len(out) < max_items:
        pos = low.find(needle, start)
        if pos < 0:
            break
        a = max(0, pos - radius)
        b = min(len(text), pos + len(token) + radius)
        snippet = " ".join(text[a:b].split())
        # Nunca publicar literales que parezcan valores de cookie/token.
        snippet = re.sub(r"(J100sessionId\s*=\s*)[^;\s\"']+", r"\1<redacted>", snippet, flags=re.I)
        out.append(snippet[:700])
        start = pos + len(token)
    return out


def audit_scheme(scheme):
    base = "%s://%s" % (scheme, PHONE_IP)
    print("=== %s SESSION BOOTSTRAP ===" % scheme.upper())

    try:
        status, headers, body = fetch(base + LOGIN_PATH)
    except (HTTPError, URLError, OSError) as exc:
        print("login=ERROR:%s" % exc.__class__.__name__)
        return

    print("login-status=%s" % status)
    print("login-content-type=%s" % headers.get("Content-Type", "no-publicado"))
    print("login-bytes=%s" % len(body))
    print("login-sha256=%s" % hashlib.sha256(body).hexdigest())

    cookies = cookie_metadata(headers)
    print("set-cookie-count=%s" % len(cookies))
    if cookies:
        for i, (name, attrs) in enumerate(cookies, 1):
            print("cookie-%02d=name:%s attrs:%s" % (i, name, ",".join(attrs) if attrs else "ninguno"))
    else:
        print("cookie-list=ninguna")

    try:
        js_status, js_headers, js_body = fetch(base + JS_PATH)
    except (HTTPError, URLError, OSError) as exc:
        print("mainjs=ERROR:%s" % exc.__class__.__name__)
        return

    js = js_body.decode("utf-8", "replace")
    print("mainjs-status=%s" % js_status)
    print("mainjs-content-type=%s" % js_headers.get("Content-Type", "no-publicado"))
    print("mainjs-bytes=%s" % len(js_body))
    print("mainjs-sha256=%s" % hashlib.sha256(js_body).hexdigest())

    for token in ("J100sessionId", "XToken", "IsWebSessionValid", "document.cookie", "Operation=33", "Operation=4"):
        found = snippets(js, token)
        print("token-%s-contexts=%s" % (re.sub(r"[^A-Za-z0-9]+", "_", token).strip("_"), len(found)))
        for i, item in enumerate(found, 1):
            print("context-%s-%02d=%s" % (re.sub(r"[^A-Za-z0-9]+", "_", token).strip("_"), i, item))


def main():
    print("=== J129 WEB SESSION BOOTSTRAP AUDIT (SOLO LECTURA) ===")
    print("Telefono=%s" % PHONE_IP)
    print("Solo GET; sin credenciales, cookies salientes ni POST")
    audit_scheme("http")
    audit_scheme("https")
    print("J129-WEB-SESSION-BOOTSTRAP-AUDIT-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
