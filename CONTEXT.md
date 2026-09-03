# CONTEXT.md — Estado consolidado Avaya J129 / Issabel 5

Actualizado: 2026-09-02

Este archivo resume el estado operativo vigente para retomar el proyecto sin reconstruir la historia. No contiene secretos reales.

## Objetivo actual

La release `v0.1.0` ya está instalada y validada server-side y físicamente en producción. El J129 registró, el operador confirmó funcionamiento correcto y la señalización de llamada Asterisk -> J129 quedó comprobada automáticamente.

La prioridad inmediata vuelve a ser optimizar Endpoint Configurator antes de iniciar trabajo funcional de v0.2.0 o construir infraestructura central de gestión de PBX.

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

## Cierre de llamada controlada — Test 47

```text
47 | J129 Production | Physical Call | Controlled E2E
workflow: .github/workflows/prod-j129-physical-call-e2e.yml
```

Historia relevante:

```text
33703875115  INFRA-BLOCKED: runner sin acceso directo al socket CLI
33710642058  preflight PASS usando helper privilegiado restringido
33711068591  llamada automatizada PASS
```

El helper root-owned instalado es:

```text
/usr/local/sbin/avaya-j129-prod-call-test
```

La llamada del run `33711068591` validó:

```text
peer SIP: 4455 READY
J129 IP: 10.3.40.32
MAC: C8:1F:EA:C3:D6:B2
respuesta SIP: 100 Trying -> 180 Ringing
Asterisk: SIP/4455 en Ringing
cleanup de SIP/RTP debug y verbose: PASS
```

No había operador físicamente junto al teléfono, por lo que `answer` y audio de ese run quedaron `NOT-TESTED`. No se usa ese run para afirmar una nueva validación física. Para v0.1.0 se considera suficiente junto con la prueba física 45 ya cerrada.

## Test 48 reservado para v0.2.0

```text
48 | Issabel Lab | J129 Remote-Originated Call | 3PCC/Control Probe
estado: NOT-TESTED
```

Objetivo futuro: probar primero en Asterisk LAB si es posible hacer que el J129 origine o acepte control remoto de una llamada real hacia otra extensión, distinguiendo claramente una llamada iniciada por el teléfono de un originate hecho por Asterisk. Solo después de evidencia LAB se evaluará producción.

## Scripts operativos y gestión futura de flota PBX

Se creó `scripts/` como catálogo permanente, no solo de pruebas. Los scripts futuros cubrirán bootstrap, deploy, diagnóstico, mantenimiento, seguridad y testing.

Visión futura documentada en:

```text
docs/pbx-fleet-control-roadmap.md
```

Objetivo de largo plazo: servidor local de distribución/control para múltiples PBX Issabel, con releases versionadas, preflight/deploy/verify/rollback, inventario, diagnóstico remoto y bootstrap de nuevas PBX, manteniendo trazabilidad parecida a GitHub Actions pero dentro de la infraestructura propia.

Esto queda como roadmap; no desplaza el trabajo inmediato sobre Endpoint Configurator.

## Seguridad de runners

```yaml
# LAB
runs-on: [self-hosted, Linux, X64, issabel-lab]

# Producción
runs-on: [self-hosted, Linux, X64, j129-production, cei-pbx02]
```

No se permite `sudo asterisk` ni shell root genérico. Las excepciones privilegiadas de producción deben ser helpers root-owned, allowlisted y con validación estricta de caller/host/argumentos.

## Discovery inter-VLAN — limitación confirmada

El scanner stock `/usr/share/issabel/privileged/detect_endpoints` solo procesa endpoints cuando nmap entrega `MAC Address:`. En misma VLAN/L2 discovery funciona; inter-VLAN/L3 responde host pero no hay MAC L2. No es fallo v0.1.0. Sprint 1 de v0.2.0: `docs/j129-v0.2.0-sprint-1.md`.

## Numeración

Fuente autoritativa: `docs/j129-test-registry.md`.

```text
45 validación física de producción — PASS
46 auditoría post-implementación read-only — PASS
47 llamada controlada — CERRADA para v0.1.0; signalling PASS, answer/audio del run NOT-TESTED
48 remote-originated call/3PCC — RESERVADA para v0.2.0 LAB
```

Próximo ID disponible: `49`.

## Próxima secuencia

```text
1. volver al Endpoint Configurator y terminar su optimización
2. identificar deuda funcional/técnica que realmente pertenezca a v0.1.x vs v0.2.0
3. convertir procedimientos repetitivos útiles en scripts reutilizables
4. mantener Test 48 reservado hasta iniciar v0.2.0 en LAB
5. no iniciar todavía PBX Fleet Controller; solo conservar roadmap y scripts reutilizables
```
