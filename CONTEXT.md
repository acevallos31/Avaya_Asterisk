# CONTEXT.md — Estado consolidado Avaya J129 / Issabel 5

## Test 56 GXP1630 — descubrimiento de fábrica — 2026-09-11

Hay un Grandstream GXP1630 de fábrica conectado a la red LAB. Test 56 inicia
con discovery automático read-only en `192.168.1.0/24` y compara las superficies
de detección HTTP con la lógica validada para GXP1625. No aplica Configure, no
escribe DB y no reinicia el teléfono.

Run `34578860986`: PASS. Se encontró exactamente un GXP1630 en
`192.168.1.169`, MAC `C0:74:AD:B4:AD:70`. La ruta legacy `/manager` no respondió,
pero `api.values.get` sí identificó el modelo. Esto demuestra compatibilidad con
la superficie moderna de detección, no todavía con login, generación cfg/XML ni
activación nativa.

## Test 55 GXP1625 — E2E manual cerrado — 2026-09-11

La IP anterior `192.168.1.167` fue reasignada por DHCP a un DVR Hikvision; el
GXP1625 exacto `C0:74:AD:E8:66:09` fue redescubierto en `192.168.1.168` por el
run read-only `34541156644`.

El run `34541419730` confirmó físicamente el factory reset del teléfono: control
exacto localizado, confirmación enviada, HTTP cayó y volvió. Su job final quedó
rojo porque Endpoint Configurator volvió a descubrir automáticamente una fila,
no porque fallara el reset.

El run read-only `34542431592` cerró el baseline post-reset con
`TEST55-POST-RESET-AUDIT=PASS`: una fila Grandstream/GXP1625 en `.168`,
`selected=0`, cero cuentas, cero override `http_password`, ambos archivos cfg
ausentes, extensiones 201/202 conservadas y HTTP 200. Asterisk aún conserva
`.168` como dirección del peer 202 con estado sanitizado `UNKNOWN`; se trata
como binding posiblemente cacheado y no como evidencia de registro activo.

El workflow de Test 55 quedó manual-only. Permite auditoría read-only
`post-config-audit`, auditoría `post-reset-audit` o `factory-reset`; el reset
requiere confirmación exacta por MAC. Producción no fue tocada.

La configuración manual ya fue ejecutada y corroborada en el run read-only
`34543757258`: `account_count=1`, asociación SIP 202 exacta, `cfg` binario y
XML presentes, XML ligado a la MAC con P35/P36=202, PBX `.10` y Ashly, HTTP 200,
peer 202 en `.168` y 201 fuera de esa IP. La auditoría general del repositorio
también pasó en `34543757263`.

El operador confirmó que la prueba manual fue satisfactoria y que el teléfono
se configuró correctamente. Test 55 queda `LAB-INTEGRATION-PASS` y
`PHYSICAL-GXP1625-PASS`, cerrado. Siguiente paso: preparar el paquete RC y el
preflight controlado de Ceiba; producción continúa sin cambios y se mantiene el
guardrail de 300 s entre Configure.

## Actualización Grandstream GXP1625 — 2026-09-10

El GXP1625 físico con firmware `1.0.7.70` alcanzó cierre E2E nativo en Issabel
LAB. H8J-a2 validó y retuvo la integración sin Chromium. H8L run
`34506170492` demostró que no se requiere User-Agent explícito. H8M run
`34507118291` completó dos Configure nativos separados 300 segundos, regeneró
`cfg<MAC>` y `cfg<MAC>.xml`, mantuvo 202/Ashly `OK` desde `192.168.1.167` y
confirmó que 201 ya no usa esa IP.

Estado: `LAB-INTEGRATION-PASS` para GXP1625 `1.0.7.70`. El parche mínimo
H6+H8J/H8M permanece activo en LAB. La ejecución H8M a 60 segundos falló de
forma segura y revirtió el cambio, por lo que producción debe iniciar con un
guardrail de 300 segundos entre Configure del mismo teléfono.

Siguiente paso: empaquetar install/verify/rollback, validar el paquete exacto
en LAB, congelar checksums y ejecutar preflight read-only en la PBX productiva
seleccionada. GXP1630 todavía requiere E2E físico independiente.

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
