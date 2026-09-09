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

## G10-17B — Read-only session diagnostic

G10-17B replaces the ambiguous P208 write precondition with a strictly read-only diagnostic. It authenticates with username/password, sends Host + Origin + Referer, retains SID and cookies without logging their values, and requests two known P-values through `/cgi-bin/api.values.get`:

```text
request=P35:P208
```

The workflow records only sanitized metadata:

- login HTTP/application response;
- SID/cookie presence only;
- API read HTTP response;
- API read application `response` and `status`;
- whether `P35` and `P208` are present;
- no DB, live-code, or phone writes.

Possible diagnostic outcomes:

```text
READ_SESSION_ACCEPTED
READ_SESSION_EXPIRED
READ_HTTP_FAILED
READ_REJECTED_OTHER
LOGIN_FAILED
```

If the read itself reports `session-expired`, the missing requirement exists before any configuration POST and the next work should focus on reproducing the browser session establishment sequence rather than patching Origin into Grandstream.py prematurely.
