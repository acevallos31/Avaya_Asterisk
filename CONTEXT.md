# CONTEXT.md — Estado consolidado Avaya J129 / Issabel 5

Actualizado: 2026-09-02

Este archivo resume el estado operativo vigente para retomar el proyecto sin reconstruir la historia. No contiene secretos reales.

## Objetivo actual

La release `v0.1.0` ya está instalada y validada server-side y físicamente en producción. El J129 registró, el operador confirmó funcionamiento correcto y la señalización de llamada Asterisk -> J129 quedó comprobada automáticamente.

La prioridad inmediata es iniciar la planificación/implementación de `v0.2.x` del Endpoint Configurator sobre una base estable, sin modificar la release congelada v0.1.0.

Arquitectura objetivo:

```text
Discovery -> fabricante/modelo -> capabilities -> Accounts estándar -> Apply Issabel
-> Extension/setAccountList -> vendor -> provisioning -> SIP
```

Para J129:

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

La llamada del run `33711068591` validó:

```text
peer SIP: 4455 READY
J129 IP: 10.3.40.32
MAC: C8:1F:EA:C3:D6:B2
respuesta SIP: 100 Trying -> 180 Ringing
Asterisk: SIP/4455 en Ringing
cleanup de SIP/RTP debug y verbose: PASS
```

No había operador físicamente junto al teléfono, por lo que `answer` y audio de ese run quedaron `NOT-TESTED`. Test 47 se considera CERRADO para v0.1.0 junto con la prueba física 45 ya completada.

## J129 v0.2.x — Sprint 1

Documento autoritativo de planificación:

```text
docs/j129-v0.2.0-sprint-1.md
```

Prioridades del Sprint 1:

```text
1. discovery/importación inter-VLAN mediante IP+MAC confiables
2. idempotencia y manejo explícito de colisiones IP/MAC
3. base de capabilities por modelo
4. idioma/locale seleccionable
5. habilitar/deshabilitar Web UI desde Endpoint Configurator
6. mapear softkeys/menú local
7. investigar/documentar conferencia tripartita
8. investigar presencia/BLF con Asterisk
9. investigar SIP TLS y certificados
10. investigar background/branding personalizado
11. investigar Auto Answer/3PCC
12. inventariar codecs/DTMF/QoS y parámetros avanzados
```

No todo debe implementarse en un único sprint, pero cada capacidad debe quedar clasificada y respaldada por evidencia antes de declararse soportada.

## Discovery inter-VLAN — limitación confirmada

El scanner stock `/usr/share/issabel/privileged/detect_endpoints` solo procesa endpoints cuando Nmap entrega `MAC Address:`. En misma VLAN/L2 discovery funciona; inter-VLAN/L3 responde host pero no hay MAC L2.

Sprint 1 debe agregar una vía complementaria basada inicialmente en `IP + MAC`, sin reemplazar el discovery local stock ni meter lógica de discovery en `Avaya.py`.

Fuentes futuras posibles: ARP del gateway, DHCP, MikroTik RouterOS/API o inventario confiable.

## Test 48 reservado para LAB

```text
48 | Issabel Lab | J129 Remote-Originated Call | 3PCC/Control Probe
estado: NOT-TESTED
```

Objetivo: probar en Asterisk LAB si es posible hacer que el J129 origine o participe en una llamada controlada hacia otra extensión, diferenciando claramente una llamada realmente originada/controlada por el teléfono de un originate hecho únicamente por Asterisk.

Decisión de secuencia: primero terminar esta actualización documental y la planificación de v0.2.x; después continuar con Test 48 en el ambiente de laboratorio.

## Modelos futuros

Se usarán ramas feature temporales para nuevos modelos, con convención conceptual:

```text
feature/avaya-j129-v0.2
feature/avaya-<modelo>
feature/<fabricante>-<modelo>
```

No mantener implementaciones divergentes permanentes por rama. La lógica común debe converger en vendor/capabilities/plantillas reutilizables.

## Scripts operativos y gestión futura de flota PBX

`scripts/` es catálogo permanente, no solo de pruebas. Los scripts futuros cubrirán bootstrap, deploy, diagnóstico, mantenimiento, seguridad y testing.

Visión futura documentada en:

```text
docs/pbx-fleet-control-roadmap.md
```

Objetivo de largo plazo: servidor local de distribución/control para múltiples PBX Issabel, con releases versionadas, preflight/deploy/verify/rollback, inventario, diagnóstico remoto y bootstrap de nuevas PBX, con trazabilidad similar a GitHub Actions dentro de infraestructura propia.

Esto queda como roadmap; no desplaza la optimización inmediata de Endpoint Configurator.

## Seguridad de runners

```yaml
# LAB
runs-on: [self-hosted, Linux, X64, issabel-lab]

# Producción
runs-on: [self-hosted, Linux, X64, j129-production, cei-pbx02]
```

No se permite `sudo asterisk` ni shell root genérico. Las excepciones privilegiadas de producción deben ser helpers root-owned, allowlisted y con validación estricta de caller/host/argumentos.

## Numeración

Fuente autoritativa: `docs/j129-test-registry.md`.

```text
45 validación física de producción — PASS
46 auditoría post-implementación read-only — PASS
47 llamada controlada — CERRADA para v0.1.0; signalling PASS, answer/audio del run NOT-TESTED
48 remote-originated call/3PCC — RESERVADA para v0.2.x LAB
```

Próximo ID disponible: `49`.

## Próxima secuencia

```text
1. mantener v0.1.0 congelada
2. crear/iniciar rama feature J129 v0.2.x cuando comience implementación
3. implementar primero discovery inter-VLAN + base de capabilities
4. continuar idioma/Web UI y capacidades avanzadas según evidencia
5. luego retomar Test 48 de llamada remota en LAB
6. después avanzar con otro modelo Avaya y posteriormente otros fabricantes
7. seguir convirtiendo procedimientos útiles en scripts reutilizables
8. PBX Fleet Controller queda como roadmap posterior
```
