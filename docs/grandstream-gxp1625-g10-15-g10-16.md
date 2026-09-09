# Grandstream GXP1625 — G10-15 result and G10-16 session propagation

## Scope

LAB only. Physical Grandstream GXP1625 at `192.168.1.167`, Endpoint Configurator target account `202 Ashly`.

This document intentionally omits SIP secrets, HTTP passwords, SID values, cookies, and binary cfg contents.

## G10-15 — Host/Referer compatibility patch

### Prior condition

G10-14 had already changed the GXP140x JSON login payload from password-only to username+password.

Direct HTTP tests established that this firmware accepts `/cgi-bin/dologin` when the request includes a Host/Referer pair coherent with the endpoint IP:

```text
Host: 192.168.1.167
Referer: http://192.168.1.167/
```

The generic implementation therefore uses `self._ip`; no site-specific tunnel hostname is hardcoded.

### Result after G10-15 apply

A real Configure action from Issabel Endpoint Configurator no longer failed at the `dologin` content-type check. The log advanced through successful JSON authentication and reached the configuration API POST.

This validates the cumulative login compatibility changes:

```text
G10-14  username + password        PASS
G10-15  Host + matching Referer    PASS
/login   JSON session established   PASS
```

## New failure observed after G10-15

The next request to the Grandstream JSON API returned an application-level session error:

```json
{
  "response": "error",
  "body": {
    "status": "session-expired"
  }
}
```

The failure occurs after successful `/cgi-bin/dologin` and during the subsequent `/cgi-bin/api.values.post` step.

The original implementation carries the returned SID in the form payload but does not explicitly propagate the `Set-Cookie` session information from the login response to the next POST. Python `http.client.HTTPConnection` maintains a TCP connection but is not a browser cookie jar.

## G10-16 — Session propagation patch

### Hypothesis

Some GXP16xx firmware requires both:

- the SID returned by `/cgi-bin/dologin` (already handled by Issabel), and
- the cookies returned by the login response to be sent with `/cgi-bin/api.values.post`.

Without cookie propagation, the phone can reject the configuration POST as `session-expired`.

### Planned change

G10-16 collects only `Set-Cookie` response headers from the successful login response, converts each to its cookie pair, and adds a `Cookie` request header for the subsequent API POST.

No SID or cookie value is printed by the workflow or helper.

Conceptual flow:

```text
POST /cgi-bin/dologin
  username + password
  Host + Referer
        |
        v
200 application/json
  SID + Set-Cookie
        |
        v
retain SID in payload
propagate Cookie header
        |
        v
POST /cgi-bin/api.values.post
```

### Guardrails

G10-16:

- runs only on the `Audit` branch and `issabel-lab` self-hosted runner;
- modifies only the live Grandstream vendor Python file;
- does not write Endpoint Configurator DB data;
- does not itself configure the phone;
- requires G10-14 and G10-15 to be present;
- creates a separate `pre-g10-16` backup;
- validates the candidate with `python3 -m py_compile` before installation;
- supports `inspect`, `apply`, and `rollback`;
- does not log cookies, SID values, passwords, SIP secrets, or cfg contents.

## Next functional test after G10-16 apply

After G10-16 reaches `session_patch_state=PATCHED`, perform one manual Configure from Issabel for the GXP1625 with target account `202 Ashly`.

Expected success criterion for this stage:

1. no `dologin answered not application/json` error;
2. no `session-expired` response from `/cgi-bin/api.values.post`;
3. Endpoint Configurator advances beyond the JSON API configuration POST.

If a new error appears after the API POST, record only the non-secret status/error text and treat it as the next isolated stage. Do not publish SID, cookie, password, SIP secret, or the binary cfg payload.
