#!/usr/bin/env python3
"""Auditoria read-only de rutas publicas del Web UI Avaya J129.

Solo realiza peticiones GET sin credenciales, cookies ni formularios. No imprime
cuerpos completos ni valores de campos. Compatible con Python 3.6.
"""

from __future__ import print_function

import hashlib
import re
import ssl
import sys
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


PHONE_IP = "192.168.1.171"
MAX_BODY = 1024 * 1024
MAX_REFERENCES = 20
MARKERS = ("login", "restart", "reboot", "management", "admin", "firmware", "upgrade")


class ReferenceParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.references = []
        self.title_parts = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        for key in ("href", "src", "action"):
            value = attrs.get(key)
            if value:
                self.references.append(value.strip())
        if tag == "meta":
            content = attrs.get("content", "")
            match = re.search(r"(?:^|;)\s*url\s*=\s*([^;]+)", content, re.I)
            if match:
                self.references.append(match.group(1).strip(" \"'"))

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
    request = Request(url, headers={"User-Agent": "Issabel-J129-ReadOnly-Audit/1.0"})
    context = None
    if url.lower().startswith("https://"):
        context = ssl._create_unverified_context()
    response = urlopen(request, timeout=8, context=context)
    try:
        body = response.read(MAX_BODY)
        return response.getcode(), response.headers, body
    finally:
        response.close()


def safe_reference(base_url, value):
    value = (value or "").strip()
    if not value or value.startswith(("#", "javascript:", "data:", "mailto:")):
        return None
    target = urljoin(base_url, value)
    parsed = urlparse(target)
    base = urlparse(base_url)
    if parsed.hostname != base.hostname:
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    return target


def discover_js_references(text):
    refs = []
    patterns = (
        r"(?:window\.)?location(?:\.href)?\s*=\s*['\"]([^'\"]+)['\"]",
        r"['\"]([^'\"]+\.(?:html?|js|css)(?:\?[^'\"]*)?)['\"]",
    )
    for pattern in patterns:
        for match in re.findall(pattern, text, re.I):
            refs.append(match)
    return refs


def audit_scheme(scheme):
    base_url = "%s://%s/" % (scheme, PHONE_IP)
    print("=== %s ROUTE MAP ===" % scheme.upper())
    try:
        status, headers, body = fetch(base_url)
    except (HTTPError, URLError, OSError) as exc:
        print("root=ERROR %s" % exc.__class__.__name__)
        return

    text = body.decode("utf-8", "replace")
    parser = ReferenceParser()
    parser.feed(text)
    raw_refs = list(parser.references)
    raw_refs.extend(discover_js_references(text))

    print("root-status=%s" % status)
    print("root-server=%s" % headers.get("Server", "no-publicado"))
    print("root-content-type=%s" % headers.get("Content-Type", "no-publicado"))
    print("root-bytes=%s" % len(body))
    print("root-sha256=%s" % hashlib.sha256(body).hexdigest())
    print("root-title=%s" % (parser.title or "no-detectado"))

    refs = []
    for value in raw_refs:
        target = safe_reference(base_url, value)
        if target and target not in refs:
            refs.append(target)
    refs = refs[:MAX_REFERENCES]

    print("same-origin-references=%s" % len(refs))
    if not refs:
        print("reference-list=ninguna")
        return

    for index, target in enumerate(refs, 1):
        parsed = urlparse(target)
        display_path = parsed.path or "/"
        if parsed.query:
            display_path += "?" + parsed.query
        print("ref-%02d=%s" % (index, display_path))
        try:
            ref_status, ref_headers, ref_body = fetch(target)
            ref_text = ref_body.decode("utf-8", "replace")
            found = [token for token in MARKERS if token in ref_text.lower()]
            print(
                "ref-%02d-result=status:%s type:%s bytes:%s sha256:%s markers:%s"
                % (
                    index,
                    ref_status,
                    ref_headers.get("Content-Type", "no-publicado"),
                    len(ref_body),
                    hashlib.sha256(ref_body).hexdigest(),
                    ",".join(found) if found else "ninguno",
                )
            )
        except (HTTPError, URLError, OSError) as exc:
            print("ref-%02d-result=ERROR:%s" % (index, exc.__class__.__name__))


def main():
    print("=== J129 WEB ROUTES AUDIT (SOLO LECTURA) ===")
    print("Telefono=%s" % PHONE_IP)
    print("Metodo=GET solamente; sin credenciales, cookies ni POST")
    audit_scheme("http")
    audit_scheme("https")
    print("J129-WEB-ROUTES-AUDIT-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
