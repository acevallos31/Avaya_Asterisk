# Grandstream model compatibility matrix

Status values in this document are evidence based. A family relationship or manufacturer document is not enough to mark a model as supported.

| Model | Physical E2E tested | Firmware tested | Discovery | Binary cfg | XML cfg | Native HTTP activation without Chromium | Reboot persistence | SIP registration verified | Status |
|---|---:|---|---|---|---|---|---|---|---|
| GXP1625 | YES | 1.0.7.70 | PASS, including OUI `C0:74:AD` | Generated | Generated and applied | PASS with endpoint credential override + H8J request/session contract | PASS | PASS, 202 at `192.168.1.167` | **SUPPORTED IN LAB** |
| GXP1630 | NO | Not tested | Not yet validated physically | Expected from current Issabel family support, not proven | Candidate same GXP16xx XML mechanism, not proven | Not tested | Not tested | Not tested | **PENDING PHYSICAL TEST** |
| Other GXP16xx | NO | Not tested | Varies by OUI/model | Do not assume | Do not assume | Do not assume | Do not assume | Do not assume | **UNVALIDATED** |
| GRP series | NO | Not tested | Separate model family | Do not assume | Manufacturer supports provisioning, but mapping differs | Do not reuse GXP1625 web/session contract without test | Not tested | Not tested | **UNVALIDATED** |

## GXP1625 validated requirements

The GXP1625 row is supported because the laboratory demonstrated the complete path:

```text
Endpoint Configurator
  -> exact endpoint/account association
  -> cfg<mac> + cfg<mac>.xml generation
  -> native HTTP login/session activation
  -> Grandstream provisioning
  -> 202 Ashly applied
  -> reboot persistence
  -> Asterisk registration from expected phone IP
```

Validated model-specific facts:

- Firmware: `1.0.7.70`.
- OUI used by physical device: `C0:74:AD`.
- Config transport validated: TFTP.
- Config Server Path validated: Issabel PBX IP without mandatory `tftp://` prefix.
- XML filename requested: `cfg<lowercase-compact-mac>.xml`.
- HTTP login requires actual endpoint administrator credential, not an incorrect model default.
- Native request fidelity requires username/password plus Content-Type, Host, Referer, Accept and the currently validated User-Agent.
- Browser-equivalent session requires `session-identity` derived from the login SID.

## GXP1630 acceptance checklist

GXP1630 must not be promoted from PENDING until a physical unit passes the following gates:

1. Discovery/OUI and model identification.
2. Correct `max_accounts` and account-slot mapping.
3. Generation of binary and XML MAC-specific files without secret exposure.
4. Confirmed request for the generated configuration from the provisioning server.
5. Successful native management login using the model's real credential behavior.
6. Successful static provisioning activation without Chromium.
7. Expected extension and display name applied to the physical phone.
8. Reboot persistence.
9. Asterisk registration from the expected IP.
10. Repeated Configure test with no destructive side effects.

If any GXP1630 firmware uses a different web API/session contract, create a model-specific branch in the vendor class rather than weakening the validated GXP1625 path.

## Versioning rule

Compatibility is tracked as **model + firmware**, not model name alone. A later firmware may change web authentication, cookies, API paths or provisioning behavior. Record every newly validated firmware in this matrix and the test ledger.
