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

## 2026-09-02 — OpenAI GPT-5.6 Sol — Test 47 cerrado para v0.1.0

Workflow:

```text
.github/workflows/prod-j129-physical-call-e2e.yml
47 | J129 Production | Physical Call | Controlled E2E
```

Evolución:

```text
33703875115  INFRA-BLOCKED: runner sin acceso directo al socket CLI
33710642058  preflight PASS mediante helper restringido
33711068591  llamada automatizada PASS
```

Para habilitar el acceso controlado se creó e instaló:

```text
deploy/j129/avaya-j129-prod-call-test
deploy/j129/avaya-j129-prod-call-test.sudoers
/usr/local/sbin/avaya-j129-prod-call-test
```

No se concedió `sudo asterisk` ni shell root genérico.

Run `33711068591`:

```text
peer 4455 READY
J129 IP 10.3.40.32
MAC C8:1F:EA:C3:D6:B2
100 Trying
180 Ringing
Asterisk mostró SIP/4455 Ringing
cleanup PASS
```

No había operador físicamente junto al J129; `answer` y audio quedaron `NOT-TESTED`. La prueba se cierra para v0.1.0 sin promover este run a evidencia física. La validación física previa 45 sigue siendo la evidencia de operación real en producción.

## 2026-09-02 — OpenAI GPT-5.6 Sol — Test 48 reservado para v0.2.0

Reservado:

```text
48 | Issabel Lab | J129 Remote-Originated Call | 3PCC/Control Probe
NOT-TESTED
```

Objetivo: investigar primero en LAB si el propio J129 puede iniciar/controlar remotamente una llamada hacia otra extensión, diferenciando ese flujo de un originate generado por Asterisk. No se hará en producción hasta tener evidencia LAB y un procedimiento controlado.

## 2026-09-02 — OpenAI GPT-5.6 Sol — Scripts operativos y roadmap de flota

La carpeta `scripts/` pasa a considerarse catálogo operativo permanente, no solo tooling de pruebas. Se documentó evolución hacia categorías de bootstrap, deploy, diagnostics, maintenance, security y testing.

Se agregó:

```text
docs/pbx-fleet-control-roadmap.md
```

Visión futura: servidor local de distribución/control para múltiples PBX Issabel, con inventario, releases aprobadas, preflight/deploy/verify/rollback, diagnósticos remotos y bootstrap de nuevas PBX. La intención es lograr una experiencia similar a GitHub Actions dentro de la red propia, sin convertir el controlador en una vía de shell root genérico.

Decisión de prioridad: no iniciar todavía el PBX Fleet Controller. Primero continuar la optimización de Endpoint Configurator; mientras tanto, todo procedimiento repetitivo útil debe tender a convertirse en script seguro, versionado e idempotente.

Archivos tocados en este cierre:

```text
docs/j129-test-registry.md
docs/pbx-fleet-control-roadmap.md
scripts/README.md
CONTEXT.md
docs/agent-log.md
```

Estado final:

```text
v0.1.0 producción: suficientemente cerrada para continuar
Test 47: CERRADA para v0.1.0
Test 48: RESERVADA v0.2.0 LAB / NOT-TESTED
PBX Fleet Controller: ROADMAP, no implementación todavía
prioridad actual: optimización Endpoint Configurator
```

Siguiente paso exacto: retomar Endpoint Configurator y revisar qué deuda/optimización conviene cerrar antes de abrir cambios funcionales de v0.2.0.
