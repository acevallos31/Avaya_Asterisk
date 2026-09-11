#!/usr/bin/env python3
import http.client
import json
import os
import urllib.parse

PHONE_IP = os.environ.get("PHONE_IP", "192.168.1.176")
USERNAME = os.environ.get("PHONE_USERNAME", "admin")
PASSWORD = os.environ.get("PHONE_PASSWORD", "")
PBX_IP = os.environ.get("PBX_IP", "192.168.1.10")
REPORT = os.environ.get("REPORT_PATH", "test64-grp2601p-auth-read.txt")
CREDENTIAL_SOURCE = os.environ.get("CREDENTIAL_SOURCE", "GRP_DEDICATED")


def log(line):
    print(line)
    with open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def request(conn, method, path, body, headers):
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    data = response.read().decode("utf-8", "replace")
    return response.status, data


open(REPORT, "w").close()
log("scope=TEST64_GRP2601P_AUTHENTICATED_READ")
log("target=GRP2601P")
log("phone_write=NO")
log("endpointconfig_write=NO")
log("firmware_upgrade=NO")

if not PASSWORD:
    log("credential_status=MISSING")
    log("diagnostic=GRANDSTREAM_GRP_HTTP_DEFAULT_PASSWORD_REQUIRED")
    log("TEST64-GRP2601P-AUTH-READ=CREDENTIAL-BLOCKED")
    raise SystemExit(0)

log("credential_status=PRESENT")
log("credential_source=" + CREDENTIAL_SOURCE)
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Host": PHONE_IP,
    "Referer": "http://%s/" % PHONE_IP,
    "Accept": "*/*",
}
conn = http.client.HTTPConnection(PHONE_IP, 80, timeout=5)
login_body = urllib.parse.urlencode({"username": USERNAME, "password": PASSWORD})
status, raw = request(conn, "POST", "/cgi-bin/dologin", login_body, headers)
try:
    login = json.loads(raw)
except Exception:
    login = {}
login_body = login.get("body")
sid = ""
if isinstance(login_body, dict):
    sid = login_body.get("sid") or ""
elif isinstance(login_body, str):
    try:
        nested_body = json.loads(login_body)
    except Exception:
        nested_body = {}
    if isinstance(nested_body, dict):
        sid = nested_body.get("sid") or ""
sid = sid or login.get("sid") or ""
accepted = status == 200 and login.get("response") == "success" and bool(sid)
log("login=" + ("SUCCESS" if accepted else "FAILED"))
log("login_http=" + str(status))
if not accepted:
    log("diagnostic=PHONE_LOGIN_CONTRACT_OR_CREDENTIAL_FAILED")
    if CREDENTIAL_SOURCE == "GXP_SINGLE_CANDIDATE":
        log("TEST64-GRP2601P-AUTH-READ=GXP-CANDIDATE-REJECTED")
    else:
        log("TEST64-GRP2601P-AUTH-READ=FAILED")
    raise SystemExit(0)

keys = "phone_model:1395:firmware_version:45:hardware_version:1397:P212:P237:P234:P235:P240:P1359:P1360:P1361:P6767"
read_body = urllib.parse.urlencode({"request": keys, "sid": sid})
status, raw = request(conn, "POST", "/cgi-bin/api.values.get", read_body, headers)
try:
    data = json.loads(raw)
except Exception:
    data = {}
body = data.get("body") if isinstance(data.get("body"), dict) else {}
read_ok = status == 200 and data.get("response") == "success" and isinstance(body, dict)
log("read=" + ("SUCCESS" if read_ok else "FAILED"))
log("read_http=" + str(status))
if not read_ok:
    log("diagnostic=PROVISIONING_STATE_READ_FAILED")
    log("TEST64-GRP2601P-AUTH-READ=FAILED")
    raise SystemExit(0)


def value(*names):
    for name in names:
        if name in body and body[name] is not None:
            return str(body[name]).strip()
    return ""


model = value("phone_model", "1395")
firmware = value("firmware_version", "45")
hardware = value("hardware_version", "1397")
log("model_match=" + ("YES" if model.replace(" ", "").upper() == "GRP2601P" else "NO"))
log("firmware=" + (firmware if firmware else "NOT_EXPOSED"))
log("hardware_present=" + ("YES" if hardware else "NO"))

p212 = value("P212")
p237 = value("P237")
log("p212_value=" + (p212 if p212 in ("0", "1", "2", "3", "4") else ("EMPTY" if not p212 else "OTHER")))
if not p237:
    target = "EMPTY"
elif p237 == PBX_IP or p237.rstrip("/") == PBX_IP:
    target = "PBX_LAB"
elif PBX_IP in p237:
    target = "PBX_LAB_URL"
else:
    target = "OTHER"
log("p237_target=" + target)
log("config_prefix_present=" + ("YES" if value("P234") else "NO"))
log("config_postfix_present=" + ("YES" if value("P235") else "NO"))
log("authenticate_config=" + (value("P240") if value("P240") in ("0", "1") else "EMPTY_OR_OTHER"))
log("xml_config_password_present=" + ("YES" if value("P1359") else "NO"))
log("config_http_username_present=" + ("YES" if value("P1360") else "NO"))
log("config_http_password_present=" + ("YES" if value("P1361") else "NO"))
log("firmware_upgrade_via=" + (value("P6767") if value("P6767") else "NOT_EXPOSED"))
log("TEST64-GRP2601P-AUTH-READ=PASS")
