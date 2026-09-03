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
RELEASE-PASS
PRODUCTION-SERVER-PASS
PRODUCTION-PHYSICAL-PASS
NOT-TESTED
```

---

## 2026-08-31 — OpenAI GPT-5.6 Sol

Se consolidó el contrato de arquitectura J129: core Issabel stock, Accounts estándar, Avaya consume `_accounts`, provisioning global -> `GET $MACADDR.txt` -> archivo por MAC, sin consultas directas de secretos desde vendor.

## 2026-09-01 — OpenAI GPT-5.6 Sol

Se validó físicamente discovery, provisioning HTTP, registro SIP y lifecycle en LAB. Se registraron `BUG-EC-001`, `BUG-J129-002`, `BUG-J129-003` y `BUG-J129-004`. `BUG-J129-003` quedó corregido server-side usando `BaseEndpoint.deleteContent()` cuando no hay cuentas. `BUG-J129-004` sigue abierto.

## 2026-09-02 — OpenAI GPT-5.6 Sol — LAB/release

### 07 — Rescan Idempotency

`LAB-INTEGRATION-PASS`: dos rescans conservaron un único endpoint, Avaya/J129 y cuenta SIP.

### 08 — Single Account V1

`LAB-INTEGRATION-PASS`:

```text
max_accounts=1
max_sip_accounts=1
max_iax2_accounts=0
```

### 09 — Remote provisioning lifecycle

`PHYSICAL-J129-PASS`, run `33599222299`.

`check-sync` produjo reinicio físico, peer down, nuevos GET de provisioning y re-registro SIP.

### 10 — Forced Provisioning / NTP

Run `33602271998`: PASS server-side. NTP generado por Issabel fue consumido físicamente tras un reinicio posterior y corrigió la hora del teléfono.

### 11 — Phone UX & Admin

Apply server-side generó parámetros de UX/nombre. La hora se corrigió después del reinicio; el menú visible no apareció. UX/menu e idioma no entran en v0.1.0.

### 12 — Production Patch

`LAB-INTEGRATION-PASS`.

```text
preflight -> install -> verify -> install -> verify -> rollback
```

### 13 — Release Package Smoke Test

El bloqueo histórico por `__pycache__` root-owned fue corregido. Run de cierre:

```text
run id: 33648748733
release exacta: 74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3
```

Resultado: `RELEASE-PASS`.

### 14 — Release Freeze Manifest

PASS. Se congelaron hashes SHA256 de la release v0.1.0 y se documentó el manifiesto.

---

## 2026-09-02 — OpenAI GPT-5.6 Sol — Producción

### Objetivo recibido

Instalar y validar de forma controlada la release exacta v0.1.0 en `cei-pbx02`, usando runner self-hosted de producción separado del LAB y sin ampliar sudo.

### Resultado

Instalación server-side completada. Workflow 15 validó:

```text
audit                PASS  run 33692817597
preflight            PASS  run 33694718272
verify               PASS  run 33695299816
install-idempotency  PASS  run 33695636455
```

Estado:

```text
PRODUCTION-SERVER-PASS
```

### Incidentes de automatización resueltos

1. PBX de producción no tiene `git`; `actions/checkout@v4` usa fallback REST API.
2. Se retiró dependencia directa de `git rev-parse` del workflow/helper.
3. Archive REST no preservó bit ejecutable de `install.sh`; helper fue corregido para usar `bash install.sh ...`.
4. Hubo ejecuciones rojas por inputs manuales incorrectos; los guards funcionaron y abortaron antes de tocar producción.

Estos incidentes fueron de harness/inputs, no regresiones de la release.

### Discovery inter-VLAN

Se confirmó que scanner stock de Issabel requiere que nmap entregue `MAC Address:`. Un host inter-VLAN responde ping/nmap pero no entrega MAC L2, por lo que discovery stock no puede completarse. Se documentó Sprint 1 v0.2.0 para resolver IP+MAC sin modificar innecesariamente core.

---

## 2026-09-02 — OpenAI GPT-5.6 Sol — Gobernanza de tests/agentes

### Objetivo recibido

- Enumerar todas las pruebas/workflows para evitar tests sin numeración.
- Mantener el formato `NN | Entorno | Componente | Propósito`.
- Endurecer separación LAB/producción de runners.
- Actualizar especialmente `AGENTS.md` y `CONTEXT.md`.
- Obligar a cualquier agente de IA a dejar documentado contexto y trabajo realizado.

### Cambios realizados

- Creado `docs/j129-test-registry.md` como fuente autoritativa de IDs.
- Preservados IDs históricos 07–15.
- Definida regla de no crear/usar pruebas sin ID.
- Actualizado `AGENTS.md` con protocolo obligatorio de entrada/handoff para agentes.
- Actualizado `CONTEXT.md` con estado real de producción, runs PASS, discovery inter-VLAN y gobernanza.
- Se identificó y comenzó a corregir riesgo de workflows LAB con `runs-on` genérico.

### Regla de handoff obligatoria

Antes de terminar cualquier sesión, todo agente debe actualizar:

```text
CONTEXT.md
docs/agent-log.md
docs/j129-test-registry.md si cambió tests/workflows/evidencia
AGENTS.md si cambió gobernanza/arquitectura/seguridad
```

Y registrar fecha, agente/modelo, objetivo, cambios, archivos, pruebas/runs, resultado, riesgos/deuda, estado final y siguiente paso.

---

## 2026-09-02 — OpenAI GPT-5.6 Sol — Cierre físico de producción

### 45 — Production Physical Validation

Identificación:

```text
45 | Production | J129 Physical Validation | Registration & Operation
```

Evidencia recibida del operador:

```text
El J129 ya registró y funciona correctamente.
```

Clasificación:

```text
PRODUCTION-PHYSICAL-PASS
```

Con este punto queda cerrado el pendiente físico principal de la v0.1.0 en producción. La release exacta ya tenía `PRODUCTION-SERVER-PASS`; ahora además cuenta con confirmación operativa física.

### Documentación actualizada

- `CONTEXT.md`
- `docs/j129-test-registry.md` — prueba 45 y próximo ID 46
- `docs/agent-log.md`

### Estado final

```text
RELEASE-PASS
PRODUCTION-SERVER-PASS
PRODUCTION-PHYSICAL-PASS
```

### Siguiente paso

Terminar la normalización de nombres de workflows y auditoría de aislamiento de runners. No modificar la release congelada v0.1.0. Las mejoras funcionales nuevas deben entrar en v0.2.0 o posterior.
