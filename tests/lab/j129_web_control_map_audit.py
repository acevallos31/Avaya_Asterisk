#!/usr/bin/env python3
"""Auditoria read-only del contrato de control Web UI Avaya J129.

Descarga /main.js con GET y extrae, sin ejecutar ninguna operacion CGI, el contrato
JavaScript alrededor de operaciones sensibles (metodo HTTP, ruta y nombres de
parametros). Compatible con Python 3.6.
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
TARGET_FUNCTIONS = (
    "SendRebootRequest",
    "AskConfirmation",
)
TARGET_OPERATIONS = ("4", "6", "33")


def fetch(url):
    req = Request(url, headers={"User-Agent": "Issabel-J129-ReadOnly-Audit/1.0"})
    context = None
    if url.lower().startswith("https://"):
        context = ssl._create_unverified_context()
    response = urlopen(req, timeout=8, context=context)
    try:
        return response.getcode(), response.headers, response.read(MAX_BODY)
    finally:
        response.close()


def compact(value):
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())


def function_body(text, name):
    match = re.search(r"function\s+%s\s*\([^)]*\)\s*\{" % re.escape(name), text, re.I)
    if not match:
        return None
    start = match.start()
    brace = text.find("{", match.start(), match.end())
    if brace < 0:
        return None
    depth = 0
    quote = None
    escaped = False
    for pos in range(brace, len(text)):
        char = text[pos]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:pos + 1]
    return None


def extract_contract(body):
    result = []
    urls = sorted(set(re.findall(r"/cgi-bin/J100WebServer\.cgi\?Operation=([0-9]+)", body, re.I)))
    methods = sorted(set(m.upper() for m in re.findall(r"\.open\(\s*['\"](GET|POST|PUT|DELETE)['\"]", body, re.I)))
    params = sorted(set(re.findall(r"['\"]([A-Za-z][A-Za-z0-9_]*)=['\"]\s*\+", body)))
    direct_params = sorted(set(re.findall(r"(?:^|[&'\"])\s*([A-Za-z][A-Za-z0-9_]*)=", body)))
    result.append("operations=%s" % (",".join(urls) if urls else "ninguna"))
    result.append("http-methods=%s" % (",".join(methods) if methods else "no-detectados"))
    names = sorted(set(params + direct_params))
    result.append("parameter-names=%s" % (",".join(names) if names else "ninguno"))
    return result


def audit_scheme(scheme):
    url = "%s://%s%s" % (scheme, PHONE_IP, PATH)
    print("=== %s CONTROL MAP ===" % scheme.upper())
    try:
        status, headers, body = fetch(url)
    except (HTTPError, URLError, OSError) as exc:
        print("result=ERROR:%s" % exc.__class__.__name__)
        return

    text = body.decode("utf-8", "replace")
    print("status=%s" % status)
    print("content-type=%s" % headers.get("Content-Type", "no-publicado"))
    print("bytes=%s" % len(body))
    print("sha256=%s" % hashlib.sha256(body).hexdigest())

    for line in extract_contract(text):
        print(line)

    for name in TARGET_FUNCTIONS:
        body_text = function_body(text, name)
        if body_text is None:
            print("function-%s=no-detectada" % name)
            continue
        normalized = compact(body_text)
        # No se imprime el cuerpo completo: solo metadatos estructurales.
        methods = sorted(set(m.upper() for m in re.findall(r"\.open\(\s*['\"](GET|POST|PUT|DELETE)['\"]", body_text, re.I)))
        operations = sorted(set(re.findall(r"Operation=([0-9]+)", body_text, re.I)))
        params = sorted(set(re.findall(r"['\"]([A-Za-z][A-Za-z0-9_]*)=['\"]\s*\+", body_text)))
        has_send = bool(re.search(r"\.send\s*\(", body_text))
        has_token = "XToken" in body_text
        print("function-%s=present" % name)
        print("function-%s-methods=%s" % (name, ",".join(methods) if methods else "no-detectados"))
        print("function-%s-operations=%s" % (name, ",".join(operations) if operations else "ninguna"))
        print("function-%s-params=%s" % (name, ",".join(params) if params else "ninguno"))
        print("function-%s-has-send=%s" % (name, "si" if has_send else "no"))
        print("function-%s-has-XToken=%s" % (name, "si" if has_token else "no"))
        print("function-%s-size=%s" % (name, len(normalized)))

    for op in TARGET_OPERATIONS:
        hits = []
        pattern = re.compile(r".{0,180}Operation=%s.{0,260}" % re.escape(op), re.I | re.S)
        for match in pattern.finditer(text):
            snippet = compact(match.group(0))
            # Redactar cualquier valor literal potencial; conservar nombres de parametros.
            snippet = re.sub(r"(psw|password|passwd|secret)=([^&'\" ]+)", r"\1=<redacted>", snippet, flags=re.I)
            hits.append(snippet[:500])
            if len(hits) >= 3:
                break
        print("operation-%s-contexts=%s" % (op, len(hits)))
        for idx, snippet in enumerate(hits, 1):
            print("operation-%s-context-%02d=%s" % (op, idx, snippet))


def main():
    print("=== J129 WEB CONTROL MAP AUDIT (SOLO LECTURA) ===")
    print("Telefono=%s" % PHONE_IP)
    print("Fuente=/main.js")
    print("Solo GET del JavaScript; no se invocan operaciones CGI")
    audit_scheme("http")
    audit_scheme("https")
    print("J129-WEB-CONTROL-MAP-AUDIT-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
