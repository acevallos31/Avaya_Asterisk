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

### Controlled change

G10-16 collected only `Set-Cookie` response headers from the successful login response, converted each to its cookie pair, and added a `Cookie` request header for the subsequent API POST.

No SID or cookie value was printed by the workflow or helper.

### Functional result

G10-16 applied successfully at the code level, but a real Endpoint Configurator Configure still returned:

```text
session-expired
```

from `/cgi-bin/api.values.post`.

Therefore the hypothesis that cookie propagation alone was the missing requirement was not validated. G10-16 was rolled back, restoring the known-good cumulative baseline of G10-14 + G10-15.

Current baseline:

```text
G10-14  username + password        APPLIED
G10-15  Host + matching Referer    APPLIED
G10-16  cookie propagation         ROLLED BACK
```

## G10-17 — Browser/API comparison

### Browser session evidence

A browser login to the GXP1625 succeeds and subsequent authenticated API calls are accepted.

Observed successful read request:

```text
POST /cgi-bin/api.values.get
HTTP 200
SID present in form body
response accepted
```

This demonstrates that the SID returned by login can be valid for a subsequent JSON API request.

### Successful browser write request

A browser Apply action generated:

```text
POST /cgi-bin/api.values.post
HTTP 200
```

Observed form payload contained a normal configuration parameter (`P208`) and did not show an explicit `sid` field in the captured payload.

The phone returned:

```json
{
  "response": "success",
  "body": {
    "status": "right"
  }
}
```

This is the first successful browser request directly comparable to Issabel's failing `/cgi-bin/api.values.post` call.

### Current diagnostic significance

Issabel currently sends its configuration variables plus `sid` in the form body and receives `session-expired`. The browser's successful `/cgi-bin/api.values.post` capture showed the configuration parameter but no explicit SID field in the visible form payload.

This raises a new, narrower hypothesis: the write endpoint may authenticate through browser session state and may reject, ignore, or conflict with an explicit `sid` field in this firmware path. This is not yet proven because the successful browser request headers still need to be compared before changing code.

### Next evidence required before G10-17 patch

Capture only the non-secret metadata from the successful browser `/cgi-bin/api.values.post` request:

- `Host`
- `Origin`
- `Referer`
- `Content-Type`
- whether a `Cookie` request header is present
- confirmation whether `sid` is absent from the form body

Do not record cookie values, SID values, passwords, SIP secrets, or full configuration payloads.

No G10-17 code patch should be applied until this header/body comparison is complete.
