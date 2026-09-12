#!/usr/bin/env python3
import hashlib
import http.client
import json
import os
import urllib.parse

IP = os.environ.get("PHONE_IP", "192.168.1.176")
USERNAME = os.environ.get("PHONE_USERNAME", "admin")
PASSWORD = os.environ.get("PHONE_PASSWORD", "")
PBX_IP = os.environ.get("PBX_IP", "192.168.1.10")
REPORT = os.environ.get("REPORT_PATH", "test65-grp2601p-bootstrap.txt")
APPLY = os.environ.get("APPLY_BOOTSTRAP", "0") == "1"
VERIFY_TARGET = os.environ.get("VERIFY_TARGET", "0") == "1"


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


def parse_json(raw):
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def classify_response(data):
    value = data.get("response") if isinstance(data, dict) else None
    if value == "success":
        return "SUCCESS"
    if value == "error":
        return "ERROR"
    return "MISSING" if value is None else "OTHER"


def read_values(conn, headers, sid):
    query = urllib.parse.urlencode({
        "pvalues": "212,237",
        "sid": sid,
        "update_session": "true",
    })
    status, raw, _ = request(
        conn, "GET", "/cgi-bin/config_get?" + query, headers=headers
    )
    data = parse_json(raw)
    configs = data.get("configs")
    values = {}
    if isinstance(configs, list):
        for item in configs:
            if not isinstance(item, dict):
                continue
            key = item.get("pvalue") or item.get("id") or item.get("name")
            if key is not None and "value" in item:
                values[str(key)] = str(item.get("value") or "")
    return status, data, values


def target_matches(values):
    return values.get("212", "") == "0" and values.get("237", "") == PBX_IP


def value_class(key, value):
    if key == "212":
        return "TARGET" if value == "0" else ("EMPTY" if not value else "OTHER")
    return "TARGET" if value == PBX_IP else ("EMPTY" if not value else "OTHER")


def update_values(conn, headers, sid, p212, p237):
    write_headers = dict(headers)
    cookie = write_headers.get("Cookie", "")
    session_cookie = "session-identity=" + sid
    write_headers["Cookie"] = (
        cookie + "; " + session_cookie if cookie else session_cookie
    )
    write_headers["Content-Type"] = "application/json"
    payload = json.dumps({
        "alias": {},
        "pvalue": {"212": p212, "237": p237},
    })
    return request(
        conn, "PUT", "/cgi-bin/config_update", payload, write_headers
    )


open(REPORT, "w").close()
log("scope", "TEST65_GRP2601P_CONTROLLED_BOOTSTRAP")
log("target_ip", IP)
log("target_mac", "EC:74:D7:1E:E8:E3")
log("apply_requested", "YES" if APPLY else "NO")
log("verify_target_requested", "YES" if VERIFY_TARGET else "NO")
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

root_status, _, root_headers = request(conn, "GET", "/", headers=headers)
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
access = parse_json(access_raw)
nonce = access.get("body", "")
nonce = nonce.strip() if isinstance(nonce, str) else ""
log("access_http", access_status)
log("access_nonce_present", "YES" if nonce else "NO")
if access_status != 200 or access.get("response") != "success" or not nonce:
    log("credential_sent", "NO")
    log("TEST65-GRP2601P-BOOTSTRAP", "ACCESS-FAILED")
    raise SystemExit(1)

password_digest = hashlib.sha256((PASSWORD + nonce).encode("utf-8")).hexdigest()
login_status, login_raw, login_headers = post_form(
    conn,
    "/cgi-bin/dologin",
    {"username": USERNAME, "password": password_digest},
    headers,
)
login = parse_json(login_raw)
payload = login.get("body")
sid = payload.strip() if isinstance(payload, str) else ""
if isinstance(payload, dict):
    sid = str(payload.get("sid") or "").strip()
sid = sid or str(login.get("sid") or "").strip()
for name, value in login_headers:
    if name.lower() == "set-cookie" and value.strip():
        pair = value.split(";", 1)[0].strip()
        cookies = [x for x in cookies if x.split("=", 1)[0] != pair.split("=", 1)[0]]
        cookies.append(pair)
if cookies:
    headers["Cookie"] = "; ".join(cookies)
login_ok = login_status == 200 and login.get("response") == "success" and bool(sid)
log("credential_sent", "HASHED")
log("login", "SUCCESS" if login_ok else "FAILED")
if not login_ok:
    log("TEST65-GRP2601P-BOOTSTRAP", "LOGIN-FAILED")
    raise SystemExit(1)

read_status, _, before = read_values(conn, headers, sid)
read_ok = read_status == 200 and "212" in before and "237" in before
log("pre_read", "SUCCESS" if read_ok else "FAILED")
log("pre_p212", value_class("212", before.get("212", "")))
log("pre_p237", value_class("237", before.get("237", "")))
if not read_ok:
    log("TEST65-GRP2601P-BOOTSTRAP", "READ-FAILED")
    raise SystemExit(1)

if not APPLY:
    matched = target_matches(before)
    log("p212_target_match", "YES" if before.get("212", "") == "0" else "NO")
    log("p237_target_match", "YES" if before.get("237", "") == PBX_IP else "NO")
    log("phone_write", "NO")
    if VERIFY_TARGET and not matched:
        log("diagnostic", "POST_REBOOT_TARGET_MISMATCH")
        log("TEST65-GRP2601P-BOOTSTRAP", "VERIFY-FAILED")
        raise SystemExit(1)
    log("diagnostic", "TARGET_VERIFY_COMPLETE" if VERIFY_TARGET else "READONLY_PREFLIGHT_COMPLETE")
    log("TEST65-GRP2601P-BOOTSTRAP", "VERIFY-PASS" if VERIFY_TARGET else "READONLY-PASS")
    raise SystemExit(0)

old_p212 = before.get("212", "")
old_p237 = before.get("237", "")
if target_matches(before):
    log("phone_write", "NO_ALREADY_CONFIGURED")
else:
    write_status, write_raw, _ = update_values(
        conn, headers, sid, "0", PBX_IP
    )
    write_data = parse_json(write_raw)
    log("write_contract", "PUT_CGI_BIN_CONFIG_UPDATE_JSON")
    log("write_http", write_status)
    log("write_response", classify_response(write_data))
    log("phone_write", "YES_CONTROLLED_P212_P237")

verify_status, _, after = read_values(conn, headers, sid)
verified = verify_status == 200 and target_matches(after)
log("post_read", "SUCCESS" if verify_status == 200 else "FAILED")
log("p212_target_match", "YES" if after.get("212", "") == "0" else "NO")
log("p237_target_match", "YES" if after.get("237", "") == PBX_IP else "NO")
if not verified:
    log("rollback_requested", "YES")
    rollback_status, rollback_raw, _ = update_values(
        conn, headers, sid, old_p212, old_p237
    )
    rollback_data = parse_json(rollback_raw)
    log("rollback_http", rollback_status)
    log("rollback_response", classify_response(rollback_data))
    _, _, rolled_back = read_values(conn, headers, sid)
    restored = (
        rolled_back.get("212", "") == old_p212
        and rolled_back.get("237", "") == old_p237
    )
    log("rollback_verified", "YES" if restored else "NO")
    log("TEST65-GRP2601P-BOOTSTRAP", "VERIFY-FAILED-ROLLED-BACK" if restored else "VERIFY-FAILED")
    raise SystemExit(1)

log("rollback_requested", "NO")
reboot_path = "/cgi-bin/api-sys_operation?" + urllib.parse.urlencode({
    "request": "REBOOT",
    "sid": sid,
})
try:
    reboot_status, reboot_raw, _ = request(
        conn, "GET", reboot_path, headers=headers
    )
    reboot_data = parse_json(reboot_raw)
    accepted = reboot_status == 200 and reboot_data.get("response") == "success"
    log("reboot_http", reboot_status)
    log("reboot_response", classify_response(reboot_data))
    log("reboot_request", "ACCEPTED" if accepted else "NOT_ACCEPTED")
except (http.client.RemoteDisconnected, ConnectionResetError, BrokenPipeError):
    accepted = True
    log("reboot_http", "CONNECTION_DROPPED")
    log("reboot_response", "NOT_AVAILABLE")
    log("reboot_request", "CONNECTION_DROPPED_AFTER_REQUEST")

log("diagnostic", "PHONE_TFTP_BOOTSTRAP_READY")
log("TEST65-GRP2601P-BOOTSTRAP", "PASS" if accepted else "PASS_REBOOT_NOT_ACCEPTED")
