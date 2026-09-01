#!/usr/bin/env python3
"""Auditoria read-only de parametros J129 actualmente servidos por el PBX.

Consulta solo /46xxsettings.txt por HTTP local y muestra parametros allowlist no
sensibles. No imprime el archivo completo ni secretos. Compatible con Python 3.6.
"""
from __future__ import print_function

import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PBX_URL = "http://127.0.0.1/46xxsettings.txt"
ALLOWLIST = (
    "ENABLE_OOD_RESET_NOTIFY",
    "ENABLE_WEBSERVER",
    "WEBSERVER_ON_HTTP",
    "FORCE_WEB_ADMIN_PASSWORD",
    "ADMIN_PASSWORD",
    "PROCPSWD",
    "PROCSTAT",
    "PROVIDE_LOGOUT",
    "ENABLE_AVAYA_ENVIRONMENT",
    "DISCOVER_AVAYA_ENVIRONMENT",
    "ENABLE_IPOFFICE",
    "ENABLE_3PCC_ENVIRONMENT",
    "HTTPSRVR",
    "HTTPPORT",
    "HTTPSPORT",
)
SENSITIVE = {"FORCE_WEB_ADMIN_PASSWORD", "ADMIN_PASSWORD", "PROCPSWD"}
MAX_BODY = 1024 * 1024


def main():
    print("=== J129 CURRENT SETTINGS AUDIT (SOLO LECTURA) ===")
    print("Fuente=%s" % PBX_URL)
    print("Solo GET local; archivo completo y secretos no se imprimen")
    req = Request(PBX_URL, headers={"User-Agent": "Issabel-J129-ReadOnly-Audit/1.0"})
    try:
        resp = urlopen(req, timeout=8)
        try:
            body = resp.read(MAX_BODY)
            status = resp.getcode()
            ctype = resp.headers.get("Content-Type", "no-publicado")
        finally:
            resp.close()
    except (HTTPError, URLError, OSError) as exc:
        print("fetch=ERROR:%s" % exc.__class__.__name__)
        return 1

    text = body.decode("utf-8", "replace")
    print("status=%s" % status)
    print("content-type=%s" % ctype)
    print("bytes=%s" % len(body))

    found = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        m = re.match(r"^SET\s+([A-Za-z0-9_]+)\s*(.*)$", line, re.I)
        if not m:
            continue
        name = m.group(1).upper()
        if name in ALLOWLIST:
            found.setdefault(name, []).append(m.group(2).strip())

    for name in ALLOWLIST:
        values = found.get(name, [])
        if not values:
            print("%s=ausente" % name)
            continue
        if name in SENSITIVE:
            print("%s=presente-redactado count=%s" % (name, len(values)))
        else:
            safe_values = []
            for value in values:
                if len(value) > 160:
                    value = value[:160] + "..."
                safe_values.append(value or "<vacio>")
            print("%s=%s" % (name, " | ".join(safe_values)))

    print("J129-CURRENT-SETTINGS-AUDIT-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
