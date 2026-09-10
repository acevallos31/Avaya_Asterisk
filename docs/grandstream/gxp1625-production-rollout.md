# Grandstream GXP1625 — controlled production rollout

## Status

Preparation only. No production PBX or phone has been modified by the G10-19
LAB work. The candidate applies only to GXP1625 firmware `1.0.7.70` until a
different firmware is validated independently.

## Required target declaration

Before creating Test 54, record all of the following:

- site and PBX hostname;
- dedicated production runner labels;
- Issabel, Endpoint Configurator, Python and Asterisk versions;
- canary phone IP, MAC and firmware;
- current SIP extension and intended SIP extension;
- expected Grandstream OUI;
- maintenance window and operator present at the phone;
- repository secret name containing the phone HTTP administrator credential;
- approved rollback owner.

Do not infer these values from the LAB or from the J129 production target.

## Release candidate contents

The package must reproduce only the validated persistent changes:

1. Grandstream OUI `C0:74:AD`, when absent and not owned by another vendor.
2. Dual generation of `cfg<mac>` and `cfg<mac>.xml` from the same P-value map.
3. Python 3.6-compatible XML serialization.
4. Redacted Grandstream error logging.
5. GXP16xx login body with username and password.
6. `Accept: */*`, Host and Referer request fidelity, without a fixed User-Agent.
7. Safe cookie preservation plus `session-identity=<SID>`.
8. Endpoint-specific `http_password` precedence; never a model-wide credential change.

The package must not contain the phone password, SIP secret, SID, cookies,
generated cfg files, raw Phone Reports or LAB addresses/accounts.

## Test 54 — production read-only preflight

Test 54 must stop before all writes and verify:

- the runner matches the declared production PBX;
- no generic self-hosted selector can reach the job;
- current `Grandstream.py` passes syntax and known-anchor checks;
- the installed package version is supported by the release candidate;
- manufacturer/model/OUI rows are unique and have no ownership collision;
- the exact canary endpoint resolves by model, MAC and IP;
- current account association and registration are recorded without secrets;
- `/tftpboot` ownership, free space and TFTP service are healthy;
- backup/state paths are writable only by root;
- the canary phone responds and its firmware matches the declared target;
- a rollback can restore the original file and DB rows.

PASS marker: `GXP1625-PRODUCTION-PREFLIGHT-PASS`. A preflight PASS does not
authorize installation.

## Controlled install sequence

```text
read-only preflight
-> explicit deployment confirmation
-> backup live Grandstream.py and affected DB rows
-> install exact frozen candidate
-> syntax/static verify
-> exact canary endpoint selection
-> one Endpoint Configurator Configure
-> cfg/XML verification without secret values
-> TFTP request evidence
-> expected SIP registration from expected phone IP
-> physical inbound/outbound/audio/DTMF confirmation
-> retain or rollback
```

Only one canary GXP1625 is processed. No bulk selection and no factory reset.

## Repeatability guardrail

For firmware `1.0.7.70`, wait at least 300 seconds before a second Configure of
the same phone. H8M showed 60 seconds can fail while 300 seconds passed twice
end to end. The cause is not labeled as rate limit, timeout, cache or session
lock without further evidence.

## Rollback triggers

Rollback immediately if any of these occurs:

- unexpected source anchor or checksum;
- DB/OUI collision;
- more than the declared canary endpoint selected;
- `Grandstream.py` syntax failure;
- missing or invalid XML/MAC binding;
- native activation failure after the controlled recovery window;
- expected SIP registration absent or previous extension remains on the phone IP;
- secrets appear in output;
- physical call/audio/DTMF fails.

Rollback restores files and DB state but does not invent or erase SIP identity
inside the phone. Record any persistent phone-side state separately.

## Promotion condition

Production support is declared only after Test 54 preflight, controlled canary
install, server-side E2E verification and operator-confirmed physical calls all
pass. Until then the model remains `SUPPORTED IN LAB`.
