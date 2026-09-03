# CONTEXT.md — Estado consolidado Avaya J129 / Issabel 5

Actualizado: 2026-09-02

Este archivo resume el estado operativo vigente para retomar el proyecto sin reconstruir la historia. No contiene secretos reales.

## Objetivo actual

La release `v0.1.0` ya está instalada y validada server-side y físicamente en producción. El J129 registró y el operador confirmó funcionamiento correcto.

Antes de cerrar definitivamente v0.1.0 se añadió una auditoría post-implementación read-only (46) y se reservó una prueba E2E de llamada física (47).

Arquitectura objetivo:

```text
Discovery -> Avaya/J129 -> Accounts estándar -> Apply Issabel
-> Extension/setAccountList -> Avaya vendor -> provisioning
-> J100Supgrade.txt -> 46xxsettings.txt -> <mac>.txt -> SIP
```

## Release congelada

```text
rama: release/j129-v0.1.0
commit: 74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3
```

Alcance: integración J129 estándar, una cuenta SIP, provisioning Avaya, Apache e installer preflight/install/verify/rollback. No incluye firmware automático, español, UX experimental, cambio automático de Web Admin password ni reboot automático durante instalación.

## Producción

```text
Host:       cei-pbx02
PBX:        10.3.40.2
OS:         Rocky Linux 8.10
Asterisk:   18.19
Python:     3.6.8
Runner:     cei-pbx02-j129-production
Usuario:    github-runner-prod
Labels:     self-hosted, Linux, X64, j129-production, cei-pbx02
```

Workflow 15:

```text
audit                PASS  run 33692817597
preflight            PASS  run 33694718272
verify               PASS  run 33695299816
install-idempotency  PASS  run 33695636455
```

Prueba física manual:

```text
45 | Production | J129 Physical Validation | Registration & Operation
PRODUCTION-PHYSICAL-PASS
```

## Auditoría post-implementación — Test 46

```text
46 | J129 Production | v0.1.0 End-to-End | Read-Only Audit
workflow: .github/workflows/prod-j129-v010-end-to-end-audit.yml
```

Primer run:

```text
run: 33701760211
job: 100482362478
resultado: HARNESS-FAIL
```

El guard de producción, checkout de `Audit` y verificación del helper pasaron. La auditoría abortó con `J129-PROD-VALIDATION-FAIL: release package missing` antes de auditar la PBX.

Causa confirmada: el helper `/usr/local/sbin/avaya-j129-prod-validation` exige por diseño el paquete congelado bajo `_release_checkout/release/j129-v0.1.0`, pero la primera versión de workflow 46 no había hecho checkout de la release exacta en esa ruta.

Esto se clasifica como fallo del harness, no fallo de la central ni de la release. No hubo mutaciones en producción.

Corrección aplicada en rama `Audit`:

```text
commit: 6bdc195bd0f6d5ef396a78fc437f9145d7209c1b
```

El workflow 46 ahora hace checkout explícito del SHA congelado `74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3` hacia `_release_checkout` antes de invocar el helper.

Siguiente ejecución recomendada:

```text
Branch: Audit
confirm: AUDIT-PROD-J129
mac: vacío
```

Primero se cerrará la auditoría general. Después se repetirá/expandirá la validación per-MAC con la MAC del J129 físico confirmado si hace falta.

## E2E físico reservado

```text
47 | J129 Production | Physical Call | Controlled E2E
```

La prueba 47 queda reservada para una llamada controlada Asterisk -> J129 y confirmación física de timbrado, answer y audio. No debe improvisarse mediante comandos genéricos ni ampliando sudo. Para automatizarla desde GitHub habrá que diseñar primero un helper privilegiado mínimo con validación estricta de peer/extensión y confirmación explícita.

## Discovery inter-VLAN — limitación confirmada

El scanner stock `/usr/share/issabel/privileged/detect_endpoints` solo procesa endpoints cuando nmap entrega `MAC Address:`. En misma VLAN/L2 discovery funciona; inter-VLAN/L3 responde host pero no hay MAC L2. No es fallo v0.1.0. Sprint 1 de v0.2.0: `docs/j129-v0.2.0-sprint-1.md`.

## Seguridad de runners

Regla obligatoria:

```yaml
# LAB
runs-on: [self-hosted, Linux, X64, issabel-lab]

# Producción
runs-on: [self-hosted, Linux, X64, j129-production, cei-pbx02]
```

Los selectores genéricos previamente detectados en 06, 26 y 29 fueron corregidos. Falta auditoría final global de workflows.

## Numeración

Fuente autoritativa: `docs/j129-test-registry.md`.

```text
00–44 pruebas históricas/workflows
45 validación física de producción — PASS
46 auditoría post-implementación read-only — primer run HARNESS-FAIL, workflow corregido
47 llamada física controlada E2E — RESERVADA
```

Próximo ID disponible: `48`.

## Bugs y deuda

- `BUG-EC-001`: `Registered at` de GUI puede quedar stale; Asterisk es autoritativo.
- `BUG-J129-002`: multicuenta no soportada en v1.
- `BUG-J129-004`: identidad SIP puede persistir localmente al retirar provisioning.
- Discovery inter-VLAN stock requiere MAC visible en L2.
- Menú local e idioma español fuera de v0.1.0.
- Completar normalización de nombres visibles y auditoría global de runners.
- Reejecutar 46 corregida antes de diseñar/ejecutar 47.

## Reglas para agentes

Leer antes de modificar: `AGENTS.md`, `CONTEXT.md`, `docs/j129-test-registry.md`, validaciones/research notes, `docs/agent-log.md`, README de release y runs/commits recientes.

Antes de terminar cualquier sesión actualizar `CONTEXT.md`, `docs/agent-log.md`, el test registry si cambian pruebas/workflows y `AGENTS.md` si cambia gobernanza/arquitectura/seguridad. Registrar objetivo, cambios, archivos, pruebas/runs, resultado, riesgos, estado y siguiente paso. Nunca guardar secretos.

## Próxima secuencia

```text
1. reejecutar workflow 46 corregido en rama Audit, sin MAC
2. revisar marcadores reales del run 46
3. si 46 queda verde, identificar/verificar la MAC física si se desea validación per-MAC
4. diseñar helper mínimo para prueba 47
5. ejecutar 47 solo con una persona físicamente junto al J129
6. terminar normalización de workflows/runners
7. cerrar v0.1.0 y luego iniciar v0.2.0
```
