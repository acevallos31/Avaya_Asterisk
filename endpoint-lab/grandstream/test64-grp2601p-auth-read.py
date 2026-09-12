#!/usr/bin/env python3
import http.client
import json
import os
import re
import urllib.parse

PHONE_IP = os.environ.get("PHONE_IP", "192.168.1.176")
USERNAME = os.environ.get("PHONE_USERNAME", "admin")
PASSWORD = os.environ.get("PHONE_PASSWORD", "")
PBX_IP = os.environ.get("PBX_IP", "192.168.1.10")
REPORT = os.environ.get("REPORT_PATH", "test64-grp2601p-auth-read.txt")
CREDENTIAL_SOURCE = os.environ.get("CREDENTIAL_SOURCE", "GRP_DEDICATED")
CONTRACT_ONLY = os.environ.get("CONTRACT_ONLY", "1") != "0"


def log(line):
    print(line)
    with open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def request(conn, method, path, body, headers):
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    data = response.read().decode("utf-8", "replace")
    return response.status, data, response.getheaders()


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
    "User-Agent": "Mozilla/5.0 EndpointConfigurator-Lab-Test64",
}
conn = http.client.HTTPConnection(PHONE_IP, 80, timeout=5)

root_status, root_raw, root_headers = request(conn, "GET", "/", None, headers)
cookie_parts = [
    value.split(";", 1)[0].strip()
    for name, value in root_headers
    if name.lower() == "set-cookie" and value.strip()
]
if cookie_parts:
    headers["Cookie"] = "; ".join(cookie_parts)
log("root_http=" + str(root_status))
log("root_cookie_present=" + ("YES" if cookie_parts else "NO"))

script_sources = sorted(set(re.findall(
    r"""<script[^>]+src=["']([^"'?#]+)""",
    root_raw,
    flags=re.IGNORECASE,
)))
contract_text = root_raw.lower()
local_script_count = 0
for source in script_sources[:12]:
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme or parsed.netloc:
        continue
    script_path = source if source.startswith("/") else "/" + source
    try:
        script_status, script_raw, _ = request(conn, "GET", script_path, None, headers)
    except Exception:
        continue
    if script_status == 200:
        local_script_count += 1
        script_lower = script_raw.lower()
        contract_text += "\n" + script_lower
        markers = [
            marker
            for marker in ("dologin", "challenge", "nonce", "sha256", "md5", "cryptojs")
            if marker in script_lower
        ]
        if "dologin" in markers or "challenge" in markers or "nonce" in markers:
            safe_name = os.path.basename(parsed.path or script_path)
            log("contract_asset=" + safe_name + ";markers=" + ",".join(markers))
            if "dologin" in markers:
                pos = script_lower.find("dologin")
                snippet = script_raw[max(0, pos - 900):pos + 1400]
                snippet = re.sub(r"\\s+", " ", snippet)
                snippet = re.sub(r"(?i)[0-9a-f]{32,}", "<HEX>", snippet)
                log("contract_dologin_context=" + snippet)
log("root_local_script_count=" + str(local_script_count))
log("contract_dologin_present=" + ("YES" if "dologin" in contract_text else "NO"))
log("contract_challenge_present=" + ("YES" if "challenge" in contract_text or "nonce" in contract_text else "NO"))
log("contract_hash_present=" + ("YES" if "sha256" in contract_text or "md5" in contract_text else "NO"))

if CONTRACT_ONLY:
    log("credential_sent=NO")
    log("TEST64-GRP2601P-CONTRACT-READ=PASS")
    raise SystemExit(0)

login_body = urllib.parse.urlencode({"username": USERNAME, "password": PASSWORD})
status, raw, _ = request(conn, "POST", "/cgi-bin/dologin", login_body, headers)
try:
    login = json.loads(raw)
except Exception:
    login = {}
login_response = login.get("response")
login_body = login.get("body")
if login_response == "success":
    response_class = "SUCCESS"
elif login_response == "error":
    response_class = "ERROR"
elif login_response is None:
    response_class = "MISSING"
else:
    response_class = "OTHER"
log("login_response_class=" + response_class)
log("login_body_type=" + type(login_body).__name__.upper())

sid = ""
if isinstance(login_body, dict):
    sid = login_body.get("sid") or ""
elif isinstance(login_body, str):
    candidate = login_body.strip()
    try:
        nested_body = json.loads(candidate)
    except Exception:
        nested_body = None
    if isinstance(nested_body, dict):
        sid = nested_body.get("sid") or ""
    elif isinstance(nested_body, str):
        sid = nested_body.strip()
    elif login_response == "success":
        sid = candidate
sid = sid or login.get("sid") or ""
accepted = status == 200 and login_response == "success" and bool(sid)
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
status, raw, _ = request(conn, "POST", "/cgi-bin/api.values.get", read_body, headers)
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
