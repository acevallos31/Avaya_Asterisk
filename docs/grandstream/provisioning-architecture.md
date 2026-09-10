# Grandstream native provisioning architecture for Issabel

## Status

Validated end-to-end on a physical Grandstream GXP1625 running firmware 1.0.7.70 against Issabel 5 / Asterisk 18.19.0.

This document describes the final mechanism proven in G10-19. It is intentionally separate from `TEST-LEDGER.md`: the ledger preserves chronology and failed hypotheses; this file describes the architecture that should be reused.

## Success definition

A supported Grandstream endpoint is considered provisioned only when all of the following occur:

1. Endpoint Configurator discovers or identifies the endpoint.
2. The correct model and account are associated with the endpoint.
3. Issabel generates a MAC-specific configuration.
4. Issabel can authenticate to the phone's HTTP management interface when static provisioning activation is needed.
5. The phone downloads the configuration from Issabel.
6. The phone applies the account configuration.
7. Asterisk confirms the expected extension registered from the expected phone IP.

A generated file by itself is not provisioning success.

## Validated GXP1625 flow

```text
Endpoint Configurator
        |
        | exact endpoint + SIP account association
        v
Grandstream.py
        |
        +--> /tftpboot/cfg<mac>       legacy binary
        |
        +--> /tftpboot/cfg<mac>.xml   Grandstream XML P-values
        |
        | HTTP management activation
        v
GXP1625 /cgi-bin/dologin
        |
        | username + password
        | Host + Referer
        | Accept: */*
        | validated curl-like User-Agent
        v
login JSON -> SID
        |
        | preserve returned cookie pairs
        | synthesize session-identity=<SID>
        v
/cgi-bin/api.values.post
        |
        | provisioning P-values
        v
Grandstream provisioning client
        |
        | TFTP, Config Server Path = Issabel PBX
        v
/tftpboot/cfg<mac> and cfg<mac>.xml
        |
        v
Account applied -> SIP REGISTER -> Asterisk verification
```

## Discovery and model identification

Grandstream manufacturer identification is OUI based. The laboratory GXP1625 uses OUI `C0:74:AD`; this OUI had to be present in Endpoint Configurator for discovery to classify the device as Grandstream.

Model identification cannot rely on the OUI alone. The tested phone exposes its model through the management API and was identified as GXP1625. Model-specific behavior must remain separate from manufacturer discovery.

## Configuration generation

Issabel's legacy Grandstream implementation generates `cfg<mac>` in binary form. On the tested GXP1625 this binary contained the correct account data but did not produce the desired account transition by itself.

The integrated solution preserves the legacy binary and additionally emits:

```text
cfg<lowercase-compact-mac>.xml
```

The XML is generated from the same P-value map as the binary file, so there is a single configuration source of truth. The XML root and MAC binding are validated before a test is considered successful.

For the GXP1625 test endpoint, safe validation confirmed the generated data represented extension 202, the Issabel PBX and account name Ashly without exposing the SIP secret.

## Provisioning server

The validated LAN transport is TFTP:

- Config Upgrade Via: `P212=0`
- Config Server Path: `P237=192.168.1.10`
- TFTP root: `/tftpboot`

The GXP1625 successfully requested both `cfg<mac>` and `cfg<mac>.xml`. Therefore `192.168.1.10` is a valid Config Server Path for this firmware when TFTP is selected; a `tftp://` prefix is not required for the validated path.

Do not assume this exact path syntax for every Grandstream family or firmware. Test it per model.

## HTTP management credential model

`model_properties.http_password` is only the model default. `endpoint_properties` overrides a property for a specific endpoint and is the correct place to handle a phone whose actual administrator password differs from the model default.

The tested GXP1625 requires an endpoint-specific `http_password` override. The value must never be written to logs, workflow summaries, artifacts or command-line arguments.

Credential precedence used by the integration:

```text
endpoint_properties.http_password
             |
             | if absent
             v
model_properties.http_password
```

Do not change a manufacturer-wide/model-wide password merely to make one physical endpoint work.

## Native HTTP session contract

The stock Issabel GXP140x-style client was not sufficient for GXP1625 firmware 1.0.7.70. The validated login request requires:

- `username` and `password` in the form body.
- `Content-Type: application/x-www-form-urlencoded`.
- `Host` for the phone IP.
- `Referer` for the phone root URL.
- `Accept: */*`.
- A User-Agent accepted by the tested firmware; the validated implementation currently uses `curl/8.14.1`.

After a successful `/cgi-bin/dologin`, the JSON response supplies a SID. Real-browser tracing established that the browser's `session-identity` value matches that SID even though it was not observed arriving as a conventional Set-Cookie value.

The final native implementation therefore preserves returned cookie pairs and adds:

```text
session-identity=<SID>
```

before calling `/cgi-bin/api.values.post`.

No SID or cookie value may be logged.

## XML and HTTP activation are separate requirements

Two independent changes were required:

- XML generation allowed the GXP1625 to consume and apply the intended account configuration.
- HTTP request/session fidelity allowed Issabel Endpoint Configurator to activate static provisioning without Chromium.

Fixing only one side is insufficient.

## Endpoint selection semantics

`issabel-endpointconfig --applyconfig` processes rows where `endpoint.selected=1` and then clears the selection flag. Automated tests must reproduce the same selection step that the GUI performs and must never leave unrelated endpoints selected.

A test may set `selected=1` only after verifying the exact manufacturer, model, MAC, IP and account association. After `applyconfig`, the expected state is `selected=0`.

## Verification and guardrails

A production-quality test should verify, at minimum:

```text
applyconfig_rc=0
grandstream_start_seen=YES
grandstream_finished_seen=YES
grandstream_failed_seen=NO
cfg<mac>.xml regenerated
expected account markers present
expected SIP extension registered from expected phone IP
previous rollback extension not registered from that same phone IP
```

Operational evidence must be sanitized. Never print raw XML, binary cfg, SIP secrets, HTTP passwords, SIDs or cookie values.

## Persisted LAB state after G10-19H8J

The validated lab intentionally retains:

- Grandstream OUI `C0:74:AD`.
- Integrated binary + XML configuration generation.
- Endpoint-specific HTTP password override for the physical GXP1625.
- Native HTTP request/session compatibility patch validated by H8I/H8J.
- Phone account 202 Ashly.

The diagnostic stage tracing used in H8K2 is not retained.

## Reuse for other Grandstream models

Reuse this architecture as a template, not as an assumption. For every new model/firmware verify independently:

- OUI and model identification.
- Number of SIP accounts.
- MAC configuration filename behavior.
- XML P-values needed for account fields.
- provisioning transport/path syntax.
- management login endpoint and request headers.
- session/cookie contract.
- activation endpoint.
- reboot behavior and persistence.
- final SIP registration.

A model is not marked supported until the physical E2E path is demonstrated.

## Related evidence

- `TEST-LEDGER.md` — chronological tests and decisions.
- `g10-19b-official-pvalue-map.md` — provisioning P-values and manufacturer references.
- GitHub Actions G10-19H8I — first native no-Chromium success.
- GitHub Actions G10-19H8J — final retained native integration.
- GitHub Actions G10-19H8K2 — repeated native POST classified as `success/right` with temporary safe tracing.
