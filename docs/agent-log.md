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

## 2026-09-02 — OpenAI GPT-5.6 Sol — Test 47 preparado

Creado en `Audit` y `main`:

```text
.github/workflows/prod-j129-physical-call-e2e.yml
47 | J129 Production | Physical Call | Controlled E2E
```

Objetivo: comprobar Asterisk -> SIP -> J129 con evidencia técnica y confirmación física.

Diseño de seguridad:

```text
mode=preflight: no origina llamada; valida acceso del runner a Asterisk CLI/logs
mode=call: requiere CALL-PROD-J129 + extensión explícita
runner: self-hosted, Linux, X64, j129-production, cei-pbx02
rama requerida: Audit
sin sudo asterisk genérico
```

La fase de llamada configura temporalmente `core set verbose 10`, `sip set debug peer <ext>` y, si se proporciona IP, `rtp set debug ip <ip>`. Usa `trap` para ejecutar siempre `sip set debug off`, `rtp set debug off` y restaurar `core set verbose 3`. Origina `SIP/<ext>` con `Playback hello-world` y conserva evidencia sanitizada como artifact.

Estado:

```text
47 IMPLEMENTADA / NOT-TESTED
```

Siguiente paso exacto: ejecutar rama `Audit`, `mode=preflight`, `confirm=PREFLIGHT-PROD-J129-CALL`. Si el runner no tiene permiso directo sobre el socket Asterisk, el run debe fallar sin llamada; en ese caso diseñar un helper privilegiado mínimo en lugar de ampliar sudo genérico.
