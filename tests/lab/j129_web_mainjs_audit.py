#!/usr/bin/env python3
"""Auditoria read-only de /main.js del Web UI Avaya J129.

Solo realiza GET sin credenciales, cookies ni POST. Extrae rutas/operaciones y
marcadores de administracion sin imprimir el JavaScript completo.
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
PATH = "/main.js"
MAX_BODY = 1024 * 1024
MARKERS = (
    "restart", "reboot", "logout", "login", "management", "firmware",
    "upgrade", "operation", "session", "password", "username", "admin",
    "J100WebServer.cgi",
)


def fetch(url):
    request = Request(url, headers={"User-Agent": "Issabel-J129-ReadOnly-Audit/1.0"})
    context = None
    if url.lower().startswith("https://"):
        context = ssl._create_unverified_context()
    response = urlopen(request, timeout=8, context=context)
    try:
        return response.getcode(), response.headers, response.read(MAX_BODY)
    finally:
        response.close()


def sanitize(value):
    return " ".join(value.split())[:220]


def extract_unique(pattern, text, flags=0, limit=50):
    values = []
    for match in re.findall(pattern, text, flags):
        if isinstance(match, tuple):
            match = next((part for part in match if part), "")
        match = sanitize(match)
        if match and match not in values:
            values.append(match)
        if len(values) >= limit:
            break
    return values


def audit_scheme(scheme):
    url = "%s://%s%s" % (scheme, PHONE_IP, PATH)
    print("=== %s MAIN.JS AUDIT ===" % scheme.upper())
    try:
        status, headers, body = fetch(url)
    except (HTTPError, URLError, OSError) as exc:
        print("result=ERROR:%s" % exc.__class__.__name__)
        return

    text = body.decode("utf-8", "replace")
    lower = text.lower()

    print("status=%s" % status)
    print("server=%s" % headers.get("Server", "no-publicado"))
    print("content-type=%s" % headers.get("Content-Type", "no-publicado"))
    print("bytes=%s" % len(body))
    print("sha256=%s" % hashlib.sha256(body).hexdigest())

    found = [marker for marker in MARKERS if marker.lower() in lower]
    print("markers=%s" % (",".join(found) if found else "ninguno"))

    operations = extract_unique(r"Operation\s*=\s*([0-9]+)", text, re.I)
    query_ops = extract_unique(r"Operation=([0-9]+)", text, re.I)
    for value in query_ops:
        if value not in operations:
            operations.append(value)
    print("operations=%s" % (",".join(operations) if operations else "ninguna"))

    cgi_refs = extract_unique(
        r"([/A-Za-z0-9_.-]*J100WebServer\.cgi(?:\?[^'\"\s)]+)?)",
        text,
        re.I,
    )
    print("cgi-references=%s" % len(cgi_refs))
    for idx, value in enumerate(cgi_refs, 1):
        print("cgi-%02d=%s" % (idx, value))

    path_refs = extract_unique(
        r"['\"]((?:/|\.\.?/)[A-Za-z0-9_./?=&%-]+)['\"]",
        text,
        re.I,
    )
    print("path-references=%s" % len(path_refs))
    for idx, value in enumerate(path_refs, 1):
        print("path-%02d=%s" % (idx, value))

    # Solo contexto corto alrededor de palabras de interes, sin volcar el JS.
    interesting = ("restart", "reboot", "logout", "management", "firmware", "upgrade", "Operation")
    snippets = []
    for token in interesting:
        for match in re.finditer(re.escape(token), text, re.I):
            start = max(0, match.start() - 90)
            end = min(len(text), match.end() + 140)
            snippet = sanitize(text[start:end])
            if snippet and snippet not in snippets:
                snippets.append(snippet)
            if len(snippets) >= 20:
                break
        if len(snippets) >= 20:
            break

    print("context-snippets=%s" % len(snippets))
    for idx, snippet in enumerate(snippets, 1):
        print("snippet-%02d=%s" % (idx, snippet))


def main():
    print("=== J129 WEB MAIN.JS AUDIT (SOLO LECTURA) ===")
    print("Telefono=%s" % PHONE_IP)
    print("Ruta=%s" % PATH)
    print("Metodo=GET solamente; sin credenciales, cookies ni POST")
    audit_scheme("http")
    audit_scheme("https")
    print("J129-WEB-MAINJS-AUDIT-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
