#!/usr/bin/env python3
import hashlib
import http.client
import json
import os
import re
import urllib.parse

IP = os.environ.get("PHONE_IP", "192.168.1.176")
USERNAME = os.environ.get("PHONE_USERNAME", "admin")
PASSWORD = os.environ.get("PHONE_PASSWORD", "")
PBX_IP = os.environ.get("PBX_IP", "192.168.1.10")
REPORT = os.environ.get("REPORT_PATH", "test65-grp2601p-bootstrap.txt")
APPLY = os.environ.get("APPLY_BOOTSTRAP", "0") == "1"


def log(key, value):
    line = "%s=%s" % (key, value)
    print(line)
    with open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def request(conn, method, path, body=None, headers=None):
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    raw = response.read().decode("utf-8", "replace")
    return response.status, raw, response.getheaders()


def post_form(conn, path, data, headers):
    return request(conn, "POST", path, urllib.parse.urlencode(data), headers)


open(REPORT, "w").close()
log("scope", "TEST65_GRP2601P_CONTROLLED_BOOTSTRAP")
log("target_ip", IP)
log("target_mac", "EC:74:D7:1E:E8:E3")
log("apply_requested", "YES" if APPLY else "NO")
log("phone_write", "PENDING" if APPLY else "NO")
log("endpointconfig_write", "NO")
log("extension_assignment", "NO")
log("configure_action", "NO")
log("firmware_upgrade", "NO")

if not PASSWORD:
    log("credential_status", "MISSING")
    log("TEST65-GRP2601P-BOOTSTRAP", "CREDENTIAL-BLOCKED")
    raise SystemExit(1)

headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "*/*",
    "Host": IP,
    "Referer": "http://%s/" % IP,
    "User-Agent": "Mozilla/5.0 EndpointConfigurator-Lab-Test65",
}
conn = http.client.HTTPConnection(IP, 80, timeout=6)

root_status, root_raw, root_headers = request(conn, "GET", "/", headers=headers)
cookies = [
    value.split(";", 1)[0].strip()
    for name, value in root_headers
    if name.lower() == "set-cookie" and value.strip()
]
if cookies:
    headers["Cookie"] = "; ".join(cookies)
log("root_http", root_status)

access_digest = hashlib.sha256(USERNAME.encode("utf-8")).hexdigest()
access_status, access_raw, _ = post_form(
    conn, "/cgi-bin/access", {"access": access_digest}, headers
)
try:
    access = json.loads(access_raw)
except Exception:
    access = {}
nonce = access.get("body", "") if isinstance(access, dict) else ""
nonce = nonce.strip() if isinstance(nonce, str) else ""
log("access_http", access_status)
log("access_nonce_present", "YES" if nonce else "NO")
if access_status != 200 or access.get("response") != "success" or not nonce:
    log("credential_sent", "NO")
    log("TEST65-GRP2601P-BOOTSTRAP", "ACCESS-FAILED")
    raise SystemExit(1)

password_digest = hashlib.sha256((PASSWORD + nonce).encode("utf-8")).hexdigest()
login_status, login_raw, _ = post_form(
    conn,
    "/cgi-bin/dologin",
    {"username": USERNAME, "password": password_digest},
    headers,
)
try:
    login = json.loads(login_raw)
except Exception:
    login = {}
payload = login.get("body")
sid = payload.strip() if isinstance(payload, str) else ""
if isinstance(payload, dict):
    sid = str(payload.get("sid") or "").strip()
sid = sid or str(login.get("sid") or "").strip()
login_ok = login_status == 200 and login.get("response") == "success" and bool(sid)
log("credential_sent", "HASHED")
log("login", "SUCCESS" if login_ok else "FAILED")
if not login_ok:
    log("TEST65-GRP2601P-BOOTSTRAP", "LOGIN-FAILED")
    raise SystemExit(1)

query = urllib.parse.urlencode({
    "pvalues": "212,237",
    "sid": sid,
    "update_session": "true",
})
read_status, read_raw, _ = request(
    conn, "GET", "/cgi-bin/config_get?" + query, headers=headers
)
try:
    read_data = json.loads(read_raw)
except Exception:
    read_data = {}
configs = read_data.get("configs") if isinstance(read_data, dict) else None
values = {}
if isinstance(configs, list):
    for item in configs:
        if isinstance(item, dict):
            key = item.get("pvalue") or item.get("id") or item.get("name")
            if key is not None and "value" in item:
                values[str(key)] = str(item.get("value") or "")
read_ok = read_status == 200 and isinstance(configs, list)
log("pre_read", "SUCCESS" if read_ok else "FAILED")
log("pre_p212", "EMPTY" if not values.get("212") else "SET")
log("pre_p237", "EMPTY" if not values.get("237") else "SET")

script_sources = sorted(set(re.findall(
    r"""<script[^>]+src=["']([^"'?#]+)""", root_raw, flags=re.IGNORECASE
)))
public_contract = []
for source in script_sources[:16]:
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme or parsed.netloc:
        continue
    path = source if source.startswith("/") else "/" + source
    try:
        status, raw, _ = request(conn, "GET", path, headers=headers)
    except Exception:
        continue
    if status != 200:
        continue
    lower = raw.lower()
    if "config_set" not in lower and "config_get" not in lower:
        continue
    asset = os.path.basename(parsed.path or path)
    endpoints = sorted(set(re.findall(
        r"""["']([^"'\\r\\n]{0,100}(?:config_set|config_get|sys_operation|reboot)[^"'\\r\\n]{0,100})["']""",
        raw,
        flags=re.IGNORECASE,
    )))
    for endpoint in endpoints[:20]:
        safe = re.sub(r"\s+", " ", endpoint)
        public_contract.append(asset + ":" + safe[:220])
    for needle in ("config_set", "config_get"):
        position = lower.find(needle)
        if position >= 0:
            snippet = raw[max(0, position - 500):position + 900]
            snippet = re.sub(r"\s+", " ", snippet)
            snippet = re.sub(r"(?i)[0-9a-f]{32,}", "<HEX>", snippet)
            log("contract_%s_context" % needle, asset + ":" + snippet[:1400])

for index, item in enumerate(public_contract[:24], start=1):
    log("contract_endpoint_%02d" % index, item)
log("config_set_present", "YES" if any("config_set" in x.lower() for x in public_contract) else "NO")
log("config_get_present", "YES" if any("config_get" in x.lower() for x in public_contract) else "NO")

if not APPLY:
    log("phone_write", "NO")
    log("diagnostic", "CONTRACT_PREFLIGHT_COMPLETE")
    log("TEST65-GRP2601P-BOOTSTRAP", "CONTRACT-PREFLIGHT-PASS")
    raise SystemExit(0)

log("phone_write", "BLOCKED_UNTIL_CONTRACT_CONFIRMED")
log("TEST65-GRP2601P-BOOTSTRAP", "APPLY-NOT-YET-IMPLEMENTED")
raise SystemExit(1)
