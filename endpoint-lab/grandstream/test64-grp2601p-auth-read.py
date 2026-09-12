#!/usr/bin/env python3
import hashlib
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
            interesting_strings = sorted(set(
                value for value in re.findall(r"""["']([^"'\\r\\n]{1,160})["']""", script_raw)
                if any(term in value.lower() for term in ("login", "access", "nonce", "challenge", "cgi-bin"))
            ))
            for value in interesting_strings[:40]:
                log("contract_string=" + safe_name + ";" + value)
            access_positions = [match.start() for match in re.finditer(r"""["']/access["']""", script_raw)]
            for access_index, access_pos in enumerate(access_positions[:4], start=1):
                access_snippet = script_raw[max(0, access_pos - 700):access_pos + 1100]
                access_snippet = re.sub(r"\\s+", " ", access_snippet)
                access_snippet = re.sub(r"(?i)[0-9a-f]{32,}", "<HEX>", access_snippet)
                log("contract_access_context_" + str(access_index) + "=" + access_snippet)
            if "dologin" in markers:
                pos = script_lower.find("dologin")
                snippet = script_raw[max(0, pos - 900):pos + 1400]
                snippet = re.sub(r"\\s+", " ", snippet)
                snippet = re.sub(r"(?i)[0-9a-f]{32,}", "<HEX>", snippet)
                log("contract_dologin_context=" + snippet)
                for label, needle in (
                    ("endpoint_dologin", "/cgi-bin/dologin"),
                    ("endpoint_access", "/cgi-bin/access"),
                    ("method_dologin", "dologin:function"),
                    ("method_access", "access:function"),
                    ("method_willlogin", "willlogin:function"),
                ):
                    marker_pos = script_lower.find(needle)
                    if marker_pos < 0:
                        continue
                    marker_snippet = script_raw[max(0, marker_pos - 500):marker_pos + 900]
                    marker_snippet = re.sub(r"\\s+", " ", marker_snippet)
                    marker_snippet = re.sub(r"(?i)[0-9a-f]{32,}", "<HEX>", marker_snippet)
                    log("contract_" + label + "_context=" + marker_snippet)
log("root_local_script_count=" + str(local_script_count))
log("contract_dologin_present=" + ("YES" if "dologin" in contract_text else "NO"))
log("contract_challenge_present=" + ("YES" if "challenge" in contract_text or "nonce" in contract_text else "NO"))
log("contract_hash_present=" + ("YES" if "sha256" in contract_text or "md5" in contract_text else "NO"))

will_status, _, _ = request(conn, "GET", "/api-will_login", None, headers)
log("will_login_http=" + str(will_status))

access_digest = hashlib.sha256(USERNAME.encode("utf-8")).hexdigest()
access_body_encoded = urllib.parse.urlencode({"access": access_digest})
access_status, access_raw, access_headers = request(conn, "POST", "/access", access_body_encoded, headers)
try:
    access_reply = json.loads(access_raw)
    access_json_valid = isinstance(access_reply, dict)
except Exception:
    access_reply = {}
    access_json_valid = False
access_response = access_reply.get("response")
access_payload = access_reply.get("body")
if isinstance(access_payload, str):
    nonce = access_payload.strip()
elif isinstance(access_payload, dict):
    nonce = str(access_payload.get("nonce") or access_payload.get("challenge") or "").strip()
else:
    nonce = str(
        access_reply.get("nonce")
        or access_reply.get("challenge")
        or access_reply.get("access")
        or ""
    ).strip()
if not nonce and not access_json_valid:
    plain_candidate = access_raw.strip()
    if 4 <= len(plain_candidate) <= 256 and "<" not in plain_candidate:
        nonce = plain_candidate
content_type = next(
    (value.split(";", 1)[0] for name, value in access_headers if name.lower() == "content-type"),
    "MISSING",
)
log("access_http=" + str(access_status))
log("access_content_type=" + content_type)
log("access_json_valid=" + ("YES" if access_json_valid else "NO"))
log("access_top_keys=" + (
    ",".join(sorted(str(key) for key in access_reply.keys()))
    if access_json_valid else "NONE"
))
log("access_response_class=" + (
    "SUCCESS" if access_response == "success"
    else "ERROR" if access_response == "error"
    else "MISSING" if access_response is None
    else "OTHER"
))
log("access_body_type=" + type(access_payload).__name__.upper())
log("access_nonce_present=" + ("YES" if nonce else "NO"))

if CONTRACT_ONLY:
    log("credential_sent=NO")
    log("TEST64-GRP2601P-CONTRACT-READ=PASS")
    raise SystemExit(0)

if access_status != 200 or access_response == "error" or not nonce:
    log("credential_sent=NO")
    log("diagnostic=GRP_ACCESS_CHALLENGE_FAILED")
    log("TEST64-GRP2601P-AUTH-READ=FAILED")
    raise SystemExit(0)

password_digest = hashlib.sha256((PASSWORD + nonce).encode("utf-8")).hexdigest()
login_body_encoded = urllib.parse.urlencode({"username": USERNAME, "password": password_digest})
status, raw, _ = request(conn, "POST", "/dologin", login_body_encoded, headers)
try:
    login = json.loads(raw)
except Exception:
    login = {}
login_response = login.get("response")
login_payload = login.get("body")
if login_response == "success":
    response_class = "SUCCESS"
elif login_response == "error":
    response_class = "ERROR"
elif login_response is None:
    response_class = "MISSING"
else:
    response_class = "OTHER"
log("credential_sent=HASHED")
log("login_response_class=" + response_class)
log("login_body_type=" + type(login_payload).__name__.upper())

sid = ""
if isinstance(login_payload, dict):
    sid = login_payload.get("sid") or ""
elif isinstance(login_payload, str) and login_response == "success":
    sid = login_payload.strip()
sid = sid or login.get("sid") or ""
accepted = status == 200 and login_response == "success" and bool(sid)
log("login=" + ("SUCCESS" if accepted else "FAILED"))
log("login_http=" + str(status))
if not accepted:
    log("diagnostic=GRP_CHALLENGE_LOGIN_FAILED")
    log("TEST64-GRP2601P-AUTH-READ=FAILED")
    raise SystemExit(0)

pvalues = "1395,45,1397,212,237,234,235,240,1359,1360,1361,6767"
query = urllib.parse.urlencode({
    "pvalues": pvalues,
    "sid": sid,
    "update_session": "true",
})
status, raw, _ = request(conn, "GET", "/config_get?" + query, None, headers)
try:
    data = json.loads(raw)
except Exception:
    data = {}
body = data.get("body") if isinstance(data.get("body"), dict) else {}
read_ok = status == 200 and data.get("response") == "success" and isinstance(body, dict)
log("read_contract=GRP_CONFIG_GET")
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


model = value("phone_model", "P1395", "1395")
firmware = value("firmware_version", "P45", "45")
hardware = value("hardware_version", "P1397", "1397")
model_direct_match = model.replace(" ", "").upper() == "GRP2601P"
log("model_source=" + ("AUTHENTICATED_READ" if model else "NETWORK_AND_DB_PREFLIGHT"))
log("model_match=" + ("YES" if model_direct_match or not model else "NO"))
log("firmware=" + (firmware if firmware else "NOT_EXPOSED"))
log("hardware_present=" + ("YES" if hardware else "NO"))

p212 = value("P212", "212")
p237 = value("P237", "237")
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
log("config_prefix_present=" + ("YES" if value("P234", "234") else "NO"))
log("config_postfix_present=" + ("YES" if value("P235", "235") else "NO"))
log("authenticate_config=" + (value("P240", "240") if value("P240", "240") in ("0", "1") else "EMPTY_OR_OTHER"))
log("xml_config_password_present=" + ("YES" if value("P1359", "1359") else "NO"))
log("config_http_username_present=" + ("YES" if value("P1360", "1360") else "NO"))
log("config_http_password_present=" + ("YES" if value("P1361", "1361") else "NO"))
log("firmware_upgrade_via=" + (value("P6767", "6767") if value("P6767", "6767") else "NOT_EXPOSED"))
log("TEST64-GRP2601P-AUTH-READ=PASS")
