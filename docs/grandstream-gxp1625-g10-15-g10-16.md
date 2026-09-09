# Grandstream GXP1625 — G10-15 to G10-17 session diagnostics

## Scope

LAB only. Physical Grandstream GXP1625 at `192.168.1.167`, Endpoint Configurator target account `202 Ashly`.

This document intentionally omits SIP secrets, HTTP passwords, SID values, cookie values, and binary cfg contents.

## G10-15 — Host/Referer compatibility patch

G10-14 had already changed the GXP140x JSON login payload from password-only to username+password.

Direct HTTP tests established that this firmware accepts `/cgi-bin/dologin` when the request includes a Host/Referer pair coherent with the endpoint IP:

```text
Host: 192.168.1.167
Referer: http://192.168.1.167/
```

After G10-15, a real Endpoint Configurator Configure no longer failed at the dologin content-type check and advanced to the configuration API POST.

```text
G10-14  username + password        PASS / APPLIED
G10-15  Host + matching Referer    PASS / APPLIED
/login   JSON session established   PASS
```

## G10-16 — Cookie propagation hypothesis

The next request to `/cgi-bin/api.values.post` returned:

```json
{
  "response": "error",
  "body": {
    "status": "session-expired"
  }
}
```

G10-16 propagated Set-Cookie values from successful dologin to the subsequent API POST while retaining the SID in the form body.

The code-level patch applied successfully, but a real Endpoint Configurator Configure still returned `session-expired`. Therefore cookie propagation alone was not sufficient. G10-16 was rolled back.

Current live baseline:

```text
G10-14  username + password        APPLIED
G10-15  Host + matching Referer    APPLIED
G10-16  cookie propagation         ROLLED BACK
```

## G10-17 — Browser/API comparison

### Successful browser read

The authenticated browser performs:

```text
POST /cgi-bin/api.values.get
HTTP 200
SID present in form body
```

The phone returns the requested values successfully. This proves a SID returned by dologin can be valid for a subsequent API request.

### Successful browser write

A browser Apply action generated:

```text
POST /cgi-bin/api.values.post
HTTP 200
```

The form body contains both a configuration parameter and `sid`. The observed harmless test parameter was `P208=2`.

The phone returned:

```json
{
  "response": "success",
  "body": {
    "status": "right"
  }
}
```

Request metadata confirmed the successful browser POST includes:

```text
Host / authority    PRESENT
Origin              PRESENT
Referer             PRESENT
Content-Type        application/x-www-form-urlencoded
Cookie              PRESENT
sid in form body    PRESENT
```

This corrects the earlier provisional observation that SID might be absent from the browser write payload.

### Diagnostic significance

Issabel already sends SID in the form body. G10-16 proved that adding cookies without Origin did not resolve `session-expired`. The clearest remaining request-shape difference observed between the successful browser POST and the Issabel path is `Origin`.

No live Grandstream.py patch is justified yet. First reproduce the browser request shape directly from the PBX.

## G10-17A — Controlled Origin/session probe

Workflow:

```text
G10-17A | Issabel Lab | GXP1625 Origin Session Probe | Controlled Test
```

Purpose:

1. authenticate through `/cgi-bin/dologin` using username + password;
2. send coherent Host + Origin + Referer headers;
3. retain SID and cookies without logging their values;
4. read `P208` first and require its current value to be exactly `2`;
5. only then POST the same `P208=2` value plus SID to `/cgi-bin/api.values.post`;
6. record only sanitized HTTP/application status.

Guardrails:

- LAB / Audit branch only;
- no DB writes;
- no live code modification;
- only an idempotent same-value phone write after a precondition read;
- GitHub Actions secret used for the HTTP password;
- SID, cookies and password values are never written to the report.

Possible outcomes:

```text
ORIGIN_BROWSER_SHAPE_ACCEPTED
ORIGIN_NOT_SUFFICIENT_SESSION_EXPIRED
ORIGIN_BROWSER_SHAPE_REJECTED
LOGIN_FAILED
PRECONDITION_FAILED
```

If `ORIGIN_BROWSER_SHAPE_ACCEPTED` is observed, the next controlled change can add Origin to the Issabel Grandstream GXP140x JSON session flow and then retest Endpoint Configurator with account 202 Ashly.
