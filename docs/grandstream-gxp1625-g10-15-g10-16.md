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

## G10-17A — Controlled Origin/session probe result

G10-17A authenticated successfully with Host + Origin + Referer and SID, but its original P208 precondition was ambiguous and the write was skipped safely.

## G10-17B — Read-only session diagnostic result

G10-17B proved a valid PBX-side authenticated read session:

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

## G10-17C — Controlled same-value write diagnostic result

The latest G10-17C run authenticated and read P208 successfully, then attempted to POST the exact same value back.

Observed sanitized result:

```text
login_http=200
login_response=success
sid_present=YES
cookie_present=NO
cookie_pair_count=0
read_http=200
read_response=success
read_p208_present=YES
same_value_write_precondition=PASS
post_http=200
post_response=error
post_status=session-expired
diagnostic=WRITE_SESSION_EXPIRED
```

The workflow itself completed successfully because `session-expired` is a diagnostic outcome, not an infrastructure failure.

The decisive difference in this run is that no usable cookie was present when the write was attempted. The read endpoint accepted SID alone, but the write endpoint did not.

## G10-17D — Read-only session cookie sequence diagnostic

G10-17D is strictly read-only and focuses on when a usable session cookie appears. It reproduces a browser-like sequence without calling `/cgi-bin/api.values.post`:

```text
dologin
  -> api.values.get (P35:P208)
  -> api-get_phone_status
  -> api.values.get (P35:P208)
```

At each step the diagnostic records only:

- HTTP/application response;
- count of new `Set-Cookie` response headers;
- cumulative cookie count;
- whether a final cookie is available.

It never records cookie values, SID, or password and performs no DB, live-code, or phone writes.

Possible decisive outcomes:

```text
COOKIE_AVAILABLE_AFTER_SEQUENCE
NO_COOKIE_AFTER_SEQUENCE
LOGIN_FAILED
```

If a cookie appears only after one of the post-login read/status calls, the next controlled write test should reproduce that exact pre-write sequence before attempting `api.values.post`.
