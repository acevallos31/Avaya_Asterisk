# Grandstream GXP1625 — G10-15 to G10-17 session diagnostics

## Scope

LAB only. Physical Grandstream GXP1625 at `192.168.1.167`, Endpoint Configurator target account `202 Ashly`.

This document intentionally omits SIP secrets, HTTP passwords, SID values, cookie values, and binary cfg contents.

## G10-15 — Host/Referer compatibility patch

G10-14 had already changed the GXP140x JSON login payload from password-only to username+password. Direct HTTP tests established that this firmware accepts `/cgi-bin/dologin` when the request includes a Host/Referer pair coherent with the endpoint IP.

After G10-15, a real Endpoint Configurator Configure no longer failed at the dologin content-type check and advanced to the configuration API POST.

```text
G10-14  username + password        PASS / APPLIED
G10-15  Host + matching Referer    PASS / APPLIED
/login   JSON session established   PASS
```

## G10-16 — Cookie propagation hypothesis

The subsequent `/cgi-bin/api.values.post` returned `session-expired`. G10-16 propagated Set-Cookie values from successful dologin to the API POST while retaining SID in the form body. A real Endpoint Configurator Configure still returned `session-expired`, so cookie propagation alone was not sufficient. G10-16 was rolled back.

Current live baseline:

```text
G10-14  username + password        APPLIED
G10-15  Host + matching Referer    APPLIED
G10-16  cookie propagation         ROLLED BACK
```

## G10-17 — Browser/API comparison

Browser evidence confirmed successful authenticated calls to both `/cgi-bin/api.values.get` and `/cgi-bin/api.values.post`. The successful browser POST includes Host/authority, Origin, Referer, Content-Type form-urlencoded, Cookie, and SID in the form body. The observed POST carried `P208=2`, which on GXP16xx corresponds to Syslog Level = INFO; it must not be treated as a generic session marker.

The phone returned:

```json
{
  "response": "success",
  "body": {
    "status": "right"
  }
}
```

The clearest remaining browser-vs-Issabel request-shape difference was Origin, but no live Grandstream.py patch is justified until the PBX-side session behavior is isolated.

## G10-17A — Controlled Origin/session probe result

G10-17A authenticated successfully and established the expected request metadata:

```text
origin_sent=YES
host_sent=YES
referer_sent=YES
login_http=200
login_json_success=YES
sid_present=YES
cookie_present=YES
```

The read-only precondition request returned HTTP 200 but did not expose a `P208` value, so the guarded POST was skipped:

```text
read_p208_http=200
read_p208_value=EMPTY
post_http=SKIPPED
probe_result=PRECONDITION_FAILED
```

This was a safe failure: no phone write was performed. The result also showed that HTTP 200 alone is insufficient evidence of an accepted authenticated API read; the application-level JSON response/status must be recorded.

## G10-17B — Read-only session diagnostic result

G10-17B authenticated with the browser-shaped headers/session and then performed:

```text
POST /cgi-bin/api.values.get
request=P35:P208
```

Observed sanitized result:

```text
login_http=200
login_response=success
sid_present=YES
cookie_present=YES
read_http=200
read_response=success
read_p35_present=YES
read_p208_present=YES
diagnostic=READ_SESSION_ACCEPTED
```

This proves the PBX can establish and reuse a valid authenticated session when Host + Origin + Referer + Cookie + SID are all present.

## G10-17C — Controlled same-value write diagnostic

G10-17C reuses the proven G10-17B session shape and adds one guarded write test. It first reads `P208`; only if that value is present does it POST the exact same current value back to `/cgi-bin/api.values.post` together with SID and the same session headers.

Guardrails:

- LAB / Audit only;
- no DB writes;
- no live code modification;
- phone write limited to `P208=<same current value>`;
- no password, SID, or cookie values are logged.

Expected decisive outcomes:

```text
WRITE_SESSION_ACCEPTED
WRITE_SESSION_EXPIRED
WRITE_REJECTED_OTHER
```

If `WRITE_SESSION_ACCEPTED` is observed, the evidence supports a final Grandstream.py compatibility patch that combines the session elements proven in G10-17B/G10-17C, followed by a real Endpoint Configurator retest for account 202 Ashly.
