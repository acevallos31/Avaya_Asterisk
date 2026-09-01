#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Dry-run J129 sobre una PBX Issabel real sin escribir en /tftpboot."""

from __future__ import print_function

import os
import py_compile
import sys
import tempfile

import tempita


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VENDOR = os.path.join(
    ROOT,
    "usr/share/issabel/endpoint-classes/class/issabel/vendor/Avaya.py",
)
J129_TEMPLATE = os.path.join(
    ROOT,
    "usr/share/issabel/endpoint-classes/tpl/Avaya_J129.tpl",
)
GLOBAL_TEMPLATE = os.path.join(
    ROOT,
    "usr/share/issabel/endpoint-classes/tpl/Avaya_global_SIP.tpl",
)


class FakeExtension(object):
    tech = "sip"
    extension = "4200"
    account = "4200"
    secret = "TEST-SIP-SECRET-NOT-REAL"
    description = "J129 LAB"


def render(path, variables):
    template = tempita.Template.from_filename(path)
    rendered = template.substitute(variables)
    # La versión de Tempita incluida en Issabel/Rocky 8 puede devolver bytes
    # bajo Python 3.6. Normalizamos a texto para validar el contenido sin
    # alterar las plantillas ni escribir archivos en /tftpboot.
    if isinstance(rendered, bytes):
        rendered = rendered.decode("utf-8")
    return rendered


def assert_contains(text, tokens):
    missing = [token for token in tokens if token not in text]
    if missing:
        raise AssertionError("Faltan tokens esperados: %r" % missing)


def main():
    print("DRY-RUN J129: inicio")
    print("Python: %s" % sys.version.split()[0])

    # Valida que Avaya.py sea sintácticamente aceptado por el Python real de Issabel.
    fd, compiled = tempfile.mkstemp(prefix="avaya-j129-", suffix=".pyc")
    os.close(fd)
    try:
        py_compile.compile(VENDOR, cfile=compiled, doraise=True)
    finally:
        if os.path.exists(compiled):
            os.unlink(compiled)
    print("PYTHON-COMPILE-PASS")

    variables = {
        "server_ip": "192.0.2.10",
        "sip": [FakeExtension()],
        "mac_address": "C8:1F:EA:AA:BB:CC",
        "config_filename": "c81feaaabbcc.txt",
        "phonesrv": "http://192.0.2.10/fake",
    }

    local = render(J129_TEMPLATE, variables)
    assert_contains(
        local,
        (
            'SET SIP_CONTROLLER_LIST "192.0.2.10:5060;transport=udp"',
            "SET SIPDOMAIN 192.0.2.10",
            'SET FORCE_SIP_USERNAME "4200"',
            'SET FORCE_SIP_PASSWORD "TEST-SIP-SECRET-NOT-REAL"',
            'SET FORCE_SIP_EXTENSION "4200"',
            'SET DISPLAY_NAME "J129 LAB"',
        ),
    )
    for forbidden in ("[GENERAL]", "[NETWORK]", "[PROVISIONING]", "default_secret"):
        if forbidden in local:
            raise AssertionError("Token prohibido en plantilla local: %s" % forbidden)
    print("J129-LOCAL-TEMPLATE-PASS")

    global_text = render(GLOBAL_TEMPLATE, {"server_ip": "192.0.2.10"})
    assert_contains(
        global_text,
        (
            "SET SIPDOMAIN 192.0.2.10",
            "SET ENABLE_3PCC_ENVIRONMENT 1",
            "GET $MACADDR.txt",
        ),
    )
    for forbidden in (
        "TEST-SIP-SECRET-NOT-REAL",
        "FORCE_SIP_PASSWORD",
        "SIPPASSWORD",
        "ADMIN_PASSWORD",
        "FORCE_WEB_ADMIN_PASSWORD",
    ):
        if forbidden in global_text:
            raise AssertionError("Dato por endpoint o credencial en global: %s" % forbidden)
    print("J129-GLOBAL-TEMPLATE-PASS")

    print("DRY-RUN-PASS: no se escribieron archivos en /tftpboot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
