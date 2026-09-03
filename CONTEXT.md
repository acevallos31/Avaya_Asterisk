# CONTEXT.md — Estado consolidado Avaya J129 / Issabel 5

Actualizado: 2026-09-02

Este archivo resume el estado operativo vigente para retomar el proyecto sin reconstruir la historia. No contiene secretos reales.

## Objetivo actual

La release `v0.1.0` ya está instalada y validada server-side, físicamente y mediante auditoría post-implementación read-only en producción. El J129 registró y el operador confirmó funcionamiento correcto.

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

## Producción

```text
Host:       cei-pbx02
PBX:        10.3.40.2
OS:         Rocky Linux 8.10
Asterisk:   18.19
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
run: 33702529808
resultado: PRODUCTION-END-TO-END-SERVER-AUDIT-PASS
```

Validó paquete congelado, DB, Apache, provisioning global, HTTP, verify oficial y provisioning per-MAC para `C8:1F:EA:C3:D6:B2`.

## E2E físico — Test 47

Workflow implementado:

```text
.github/workflows/prod-j129-physical-call-e2e.yml
47 | J129 Production | Physical Call | Controlled E2E
```

Tiene dos modos:

```text
preflight  -> no origina llamada; valida acceso del runner a Asterisk CLI y disponibilidad de logs
call       -> valida peer, eleva verbose temporalmente, activa SIP debug específico, RTP debug por IP si se indica, origina SIP/<ext> con Playback hello-world, captura evidencia y siempre desactiva debug/restaura verbose mediante trap
```

El workflow no concede `sudo asterisk` genérico. Primero debe ejecutarse `preflight` en rama `Audit` con confirmación `PREFLIGHT-PROD-J129-CALL`. Si el runner no puede acceder directamente al socket CLI, la prueba debe fallar sin originar llamada y se decidirá un helper mínimo privilegiado.

La fase `call` requiere confirmación `CALL-PROD-J129`, extensión numérica explícita y, opcionalmente, IP del J129 para RTP debug específico. Después del run sigue siendo obligatoria confirmación humana de timbrado, answer y audio.

## Discovery inter-VLAN — limitación confirmada

El scanner stock `/usr/share/issabel/privileged/detect_endpoints` solo procesa endpoints cuando nmap entrega `MAC Address:`. En misma VLAN/L2 discovery funciona; inter-VLAN/L3 responde host pero no hay MAC L2. No es fallo v0.1.0. Sprint 1 de v0.2.0: `docs/j129-v0.2.0-sprint-1.md`.

## Seguridad de runners

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
46 auditoría post-implementación read-only — PASS run 33702529808
47 llamada física controlada E2E — IMPLEMENTADA / pendiente preflight
```

Próximo ID disponible: `48`.

## Bugs y deuda

- `BUG-EC-001`: `Registered at` de GUI puede quedar stale; Asterisk es autoritativo.
- `BUG-J129-002`: multicuenta no soportada en v1.
- `BUG-J129-004`: identidad SIP puede persistir localmente al retirar provisioning.
- Discovery inter-VLAN stock requiere MAC visible en L2.
- Menú local e idioma español fuera de v0.1.0.
- Completar normalización de nombres visibles y auditoría global de runners.

## Reglas para agentes

Leer antes de modificar: `AGENTS.md`, `CONTEXT.md`, `docs/j129-test-registry.md`, validaciones/research notes, `docs/agent-log.md`, README de release y runs/commits recientes.

Antes de terminar cualquier sesión actualizar `CONTEXT.md`, `docs/agent-log.md`, el test registry si cambian pruebas/workflows y `AGENTS.md` si cambia gobernanza/arquitectura/seguridad. Registrar objetivo, cambios, archivos, pruebas/runs, resultado, riesgos, estado y siguiente paso. Nunca guardar secretos.

## Próxima secuencia

```text
1. ejecutar workflow 47 en rama Audit, mode=preflight, confirm=PREFLIGHT-PROD-J129-CALL
2. revisar si github-runner-prod puede acceder a Asterisk CLI y al full log sin privilegios adicionales
3. si preflight PASS, ejecutar 47 mode=call solo cuando haya alguien junto al J129
4. confirmar físicamente ring/answer/audio y revisar artifact sanitizado
5. terminar normalización de workflows/runners
6. cerrar v0.1.0 y luego iniciar v0.2.0
```
