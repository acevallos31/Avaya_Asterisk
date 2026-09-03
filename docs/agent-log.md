# Agent Audit Log

Registro compartido de trabajo humano/IA en `Avaya_Asterisk`. Consultar primero `AGENTS.md`, `CONTEXT.md` y `docs/j129-test-registry.md`. No almacenar secretos reales.

Estados usados:

```text
STATIC-PASS
LAB-READ-PASS
LAB-INTEGRATION-PASS
LAB-FIX-PASS
PHYSICAL-J129-PASS
INFRA-BLOCKED
HARNESS-FAIL
RELEASE-PASS
PRODUCTION-SERVER-PASS
PRODUCTION-PHYSICAL-PASS
PRODUCTION-END-TO-END-SERVER-AUDIT-PASS
NOT-TESTED
```

---

## 2026-08-31 — OpenAI GPT-5.6 Sol

Se consolidó el contrato de arquitectura J129: core Issabel stock, Accounts estándar, Avaya consume `_accounts`, provisioning global -> `GET $MACADDR.txt` -> archivo por MAC, sin consultas directas de secretos desde vendor.

## 2026-09-01 — OpenAI GPT-5.6 Sol

Se validó físicamente discovery, provisioning HTTP, registro SIP y lifecycle en LAB. Se registraron bugs y deuda de comportamiento del J129.

## 2026-09-02 — OpenAI GPT-5.6 Sol — LAB/release

07–14 quedaron validados/documentados: rescan idempotente, single-account, lifecycle físico, NTP, UX/admin, production patch, smoke test exacto y freeze manifest. Release congelada: `74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3`.

## 2026-09-02 — OpenAI GPT-5.6 Sol — Producción

Workflow 15 validó:

```text
audit                PASS  run 33692817597
preflight            PASS  run 33694718272
verify               PASS  run 33695299816
install-idempotency  PASS  run 33695636455
```

Estado: `PRODUCTION-SERVER-PASS`.

## 2026-09-02 — OpenAI GPT-5.6 Sol — Cierre físico de producción

```text
45 | Production | J129 Physical Validation | Registration & Operation
PRODUCTION-PHYSICAL-PASS
```

El operador confirmó que el J129 registró y funciona correctamente.

## 2026-09-02 — OpenAI GPT-5.6 Sol — Test 46

Primer run `33701760211`: `HARNESS-FAIL` por ausencia del checkout de la release congelada. No se auditó ni modificó la PBX. Se corrigió el workflow en commit `6bdc195bd0f6d5ef396a78fc437f9145d7209c1b`.

Run válido:

```text
33702529808
PRODUCTION-END-TO-END-SERVER-AUDIT-PASS
```

Marcadores observados:

```text
J129-PROD-FROZEN-PACKAGE-PASS
J129-PROD-SERVER-AUDIT-PASS
J129-PROD-PROVISIONING-AUDIT-PASS
J129-PROD-E2E-RELEASE-VERIFY-PASS
J129-PROD-E2E-HTTP-PASS
J129-PROD-E2E-APACHE-PASS
J129-PROD-MAC-PROVISIONING-PASS=c81feac3d6b2
```

La MAC validada fue `C8:1F:EA:C3:D6:B2`.

## 2026-09-02 — OpenAI GPT-5.6 Sol — Test 47

Workflow:

```text
.github/workflows/prod-j129-physical-call-e2e.yml
47 | J129 Production | Physical Call | Controlled E2E
```

Primer preflight:

```text
run: 33703875115
resultado: INFRA-BLOCKED
```

Guard de producción PASS. El runner `github-runner-prod` no puede abrir el socket CLI de Asterisk:

```text
Unable to connect to remote asterisk (does /var/run/asterisk/asterisk.ctl exist?)
```

No se originó ninguna llamada. La evidencia del run se guardó como artifact.

Se preparó, pero NO se instaló en producción, un helper privilegiado mínimo:

```text
deploy/j129/avaya-j129-prod-call-test
deploy/j129/avaya-j129-prod-call-test.sudoers
```

El helper valida `SUDO_USER=github-runner-prod`, host `cei-pbx02`, extensión e IP, y solo permite `preflight`, `peer`, `call` y `cleanup`. La fase `call` usa verbose 10, SIP debug específico y RTP debug opcional, origina `SIP/<ext> application Playback hello-world` y siempre restaura debug/verbose.

El workflow 47 se actualizó en `Audit` y `main` para usar exclusivamente `/usr/local/sbin/avaya-j129-prod-call-test`; no se concede `sudo asterisk` ni shell root genérico.

Estado final:

```text
47 INFRA-BLOCKED
helper/sudoers STAGED, NOT-INSTALLED
```

Siguiente paso exacto: con acceso root a `cei-pbx02`, instalar el helper como `root:root 0755`, instalar la regla sudoers como `root:root 0440`, validar con `visudo -cf`, y reejecutar `47` en rama `Audit`, `mode=preflight`, `confirm=PREFLIGHT-PROD-J129-CALL`. Solo después de preflight PASS se ejecutará `mode=call` con una persona físicamente junto al J129.
