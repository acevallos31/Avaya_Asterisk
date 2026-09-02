# CONTEXT.md — Estado consolidado Avaya J129 / Issabel 5

Actualizado: 2026-09-02

Este archivo resume el estado operativo vigente para retomar el proyecto sin reconstruir la historia. No contiene secretos reales.

## Objetivo actual

La release `v0.1.0` ya está instalada y validada server-side en producción. El siguiente objetivo es cerrar seguridad/gobernanza de workflows y ejecutar una prueba física controlada con un J129 localizable.

Arquitectura objetivo:

```text
Discovery -> Avaya/J129 -> Accounts estándar -> Apply Issabel
-> Extension/setAccountList -> Avaya vendor -> provisioning
-> J100Supgrade.txt -> 46xxsettings.txt -> <mac>.txt -> SIP
```

## Release congelada

Rama:

```text
release/j129-v0.1.0
```

Commit exacto:

```text
74d3f4cc1c2d5a432ad69e3c105b7fd3db00b6f3
```

Alcance:

- Avaya J129 en Endpoint Configurator estándar;
- una cuenta SIP;
- provisioning Avaya;
- Apache provisioning;
- installer preflight/install/verify/rollback;
- sin firmware automático;
- sin español;
- sin menú UX experimental;
- sin cambio automático de Web Admin password;
- sin reboot automático durante instalación.

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

Instalación v0.1.0: completada.

Validación automática workflow 15:

```text
audit                PASS  run 33692817597
preflight            PASS  run 33694718272
verify               PASS  run 33695299816
install-idempotency  PASS  run 33695636455
```

Clasificación actual:

```text
PRODUCTION-SERVER-PASS
```

No declarar todavía `PRODUCTION-PHYSICAL-PASS`.

## Evidencia server-side física preparada

En producción ya se validó anteriormente generación/HTTP de:

```text
J100Supgrade.txt
46xxsettings.txt
<mac>.txt
```

Un J129 descubierto/configurado temporalmente generó correctamente provisioning por MAC, pero no se completó lifecycle físico porque no se pudo localizar físicamente ese teléfono. Se decidió desconfigurarlo y usar un equipo localizable para la prueba definitiva.

## Discovery inter-VLAN — limitación confirmada

El scanner stock `/usr/share/issabel/privileged/detect_endpoints` usa nmap y solo procesa endpoints cuando la salida incluye `MAC Address:`.

En la misma VLAN/L2:

```text
Host up + MAC Address -> discovery posible
```

Inter-VLAN/L3:

```text
Host up + sin MAC Address -> Issabel stock no crea/discrimina endpoint
```

No es fallo de v0.1.0. Sprint 1 de v0.2.0 documentado en:

```text
docs/j129-v0.2.0-sprint-1.md
```

La solución futura debe obtener IP+MAC desde una fuente autoritativa sin modificar innecesariamente el core de Issabel.

## Seguridad de self-hosted runners

Se detectó deuda importante: algunos workflows LAB históricos usan selectores genéricos como:

```yaml
runs-on: self-hosted
```

o:

```yaml
runs-on: [self-hosted, Linux, X64]
```

Eso puede hacer que GitHub asigne accidentalmente un job LAB al runner de producción porque este también posee las etiquetas automáticas `self-hosted`, `Linux`, `X64`.

Regla obligatoria:

```yaml
# LAB
runs-on: [self-hosted, Linux, X64, issabel-lab]

# Producción
runs-on: [self-hosted, Linux, X64, j129-production, cei-pbx02]
```

Antes de nuevas pruebas físicas hay que completar la normalización de los workflows LAB con selector genérico.

## Numeración de pruebas

Fuente autoritativa:

```text
docs/j129-test-registry.md
```

Formato:

```text
NN | Entorno | Componente | Propósito
```

Los IDs 07–15 ya tienen evidencia histórica y no deben renumerarse. Todos los workflows auxiliares/históricos también reciben ID para evitar pruebas sin numeración.

Resumen principal:

```text
01 baseline read-only
02 endpoint DB
03 discovery
04 provisioning
05 SIP registration
06 apply config
07 rescan idempotency
08 single account v1
09 remote provisioning lifecycle
10 forced provisioning / NTP
11 phone UX & admin
12 production patch LAB
13 release package smoke
14 freeze manifest
15 production server validation
16–44 diagnósticos/helpers/probes históricos registrados
```

## LAB histórico

```text
Issabel:    5
OS:         Rocky Linux 8
Asterisk:   18.19.0
Python:     3.6.8
PBX:        192.168.1.10
J129:       192.168.1.168
MAC:        C8:1F:EA:9B:65:0D
Firmware:   3.0.0.0.20
Endpoint:   id 3
SIP:        200
Runner:     github-runner / issabel-lab
```

Evidencia histórica importante:

```text
07 PASS — rescan idempotente
08 PASS — una cuenta SIP
09 PHYSICAL-J129-PASS — check-sync reinicia y reprovisiona
10 PASS server-side — NTP consumido físicamente tras reboot posterior
11 UX — hora correcta, menú visible no apareció
12 PASS — install/verify/idempotencia/rollback LAB
13 RELEASE-PASS — package smoke exacto
14 PASS — freeze/checksums
15 PRODUCTION-SERVER-PASS — audit/preflight/verify/idempotency
```

## Bugs y deuda

- `BUG-EC-001`: `Registered at` de GUI puede quedar stale; Asterisk es autoritativo.
- `BUG-J129-002`: multicuenta no soportada en v1.
- `BUG-J129-004`: identidad SIP puede persistir localmente al retirar provisioning.
- Discovery inter-VLAN stock requiere MAC visible en L2.
- Menú local e idioma español fuera de v0.1.0.
- Algunos workflows LAB históricos necesitan selector `issabel-lab` explícito.
- Nombres visibles de workflows históricos deben quedar sincronizados con `docs/j129-test-registry.md`.

## Reglas para agentes

Leer antes de modificar:

1. `AGENTS.md`
2. `CONTEXT.md`
3. `docs/j129-test-registry.md`
4. `docs/j129-lab-validation.md`
5. `docs/j129-research-notes.md`
6. `docs/agent-log.md`
7. README de release si aplica
8. commits/runs recientes

Antes de terminar cualquier sesión de trabajo, el agente debe actualizar:

```text
CONTEXT.md
docs/agent-log.md
docs/j129-test-registry.md si cambió tests/workflows
AGENTS.md si cambió gobernanza/arquitectura/seguridad
```

El handoff debe incluir objetivo, cambios, archivos, pruebas/runs, resultado, riesgos, estado final y siguiente paso. No escribir secretos.

## Próxima secuencia

```text
1. normalizar selectores de runner LAB que todavía sean genéricos
2. normalizar nombres visibles de workflows contra j129-test-registry.md
3. verificar que ningún LAB pueda caer en cei-pbx02-j129-production
4. seleccionar un J129 físico localizable en la red de producción
5. discovery en misma VLAN/L2
6. asignar extensión desde Endpoint Configurator
7. Apply
8. validar GET de J100Supgrade/46xxsettings/<mac>.txt
9. validar registro SIP
10. llamadas entrante/saliente y audio
11. documentar PRODUCTION-PHYSICAL-PASS solo si todo lo anterior pasa
```
