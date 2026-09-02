#!/usr/bin/env python3
"""Baseline read-only para J129 forced provisioning.

Audita hora/NTP de la PBX y parametros temporales no sensibles actualmente
servidos en 46xxsettings.txt. No modifica servicios ni provisioning.
Compatible con Python 3.6.
"""
from __future__ import print_function

import re
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PBX_URL = "http://127.0.0.1/46xxsettings.txt"
PARAMS = (
    "SNTPSRVR",
    "SNTP_SYNC_INTERVAL",
    "TIMEZONE",
    "TIMEZONEOFFSET",
    "DSTOFFSET",
    "DSTSTART",
    "DSTSTOP",
    "DATETIMEFORMAT",
    "DATEFORMAT",
    "TIMEFORMAT",
)
MAX_BODY = 1024 * 1024


def run(cmd):
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = p.communicate()[0].decode("utf-8", "replace").strip()
        return p.returncode, out
    except OSError as exc:
        return 127, exc.__class__.__name__


def safe_print_command(label, cmd):
    rc, out = run(cmd)
    print("%s_rc=%s" % (label, rc))
    if out:
        for line in out.splitlines()[:30]:
            print("%s: %s" % (label, line))
    return rc, out


def fetch_settings():
    req = Request(PBX_URL, headers={"User-Agent": "Issabel-J129-Forced-Provisioning-Baseline/1.0"})
    try:
        resp = urlopen(req, timeout=8)
        try:
            body = resp.read(MAX_BODY)
            status = resp.getcode()
        finally:
            resp.close()
    except (HTTPError, URLError, OSError) as exc:
        print("settings_fetch=ERROR:%s" % exc.__class__.__name__)
        return None

    print("settings_status=%s" % status)
    print("settings_bytes=%s" % len(body))
    return body.decode("utf-8", "replace")


def audit_params(text):
    found = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        m = re.match(r"^SET\s+([A-Za-z0-9_]+)\s*(.*)$", line, re.I)
        if not m:
            continue
        name = m.group(1).upper()
        if name in PARAMS:
            found.setdefault(name, []).append(m.group(2).strip())

    for name in PARAMS:
        values = found.get(name, [])
        if values:
            print("%s=%s" % (name, " | ".join(values)))
        else:
            print("%s=ausente" % name)


def main():
    print("=== J129 FORCED PROVISIONING BASELINE AUDIT ===")
    print("MODO=READ-ONLY")

    safe_print_command("date", ["date", "--iso-8601=seconds"])
    safe_print_command("timedatectl", ["timedatectl", "status"])

    chronyc_rc, _ = safe_print_command("chronyc_tracking", ["chronyc", "tracking"])
    if chronyc_rc == 127:
        print("chronyc=NO-DISPONIBLE")

    rc, out = run(["ss", "-lun"])
    print("udp_listener_audit_rc=%s" % rc)
    ntp_listener = False
    if rc == 0:
        for line in out.splitlines():
            if re.search(r"(?:^|[:.])123\s", line) or re.search(r":123(?:\s|$)", line):
                print("udp123_listener=%s" % line.strip())
                ntp_listener = True
    print("PBX_UDP123_LISTENER=%s" % ("YES" if ntp_listener else "NO"))

    text = fetch_settings()
    if text is None:
        return 1
    audit_params(text)

    print("J129-FORCED-PROVISIONING-BASELINE-AUDIT-PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
