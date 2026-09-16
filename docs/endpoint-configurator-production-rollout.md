# Endpoint Configurator — plan de despliegue a producción

Fecha de preparación: 2026-09-14. Actualizado: 2026-09-16.

## Alcance del candidato

Este gate cubre exclusivamente la fundación de credenciales administrativas del
Endpoint Configurator y la visualización de cuentas/registro en la tabla
principal. No autoriza firmware, factory reset, cambio de extensión, `Configure`
ni escritura a teléfonos.

Superficie funcional validada en LAB:

- contraseña administrativa global por PBX y override por MAC cifrados en reposo;
- credencial inicial `FACTORY` por MAC;
- clave externa `/etc/issabel/endpoint-configurator.key` con
  `root:asterisk:0640`;
- importación CSV controlada `mac_address,password`;
- columna `Extension / Registration` en la tabla principal;
- resumen read-only de cuentas asignadas y estado SIP/IAX2/PJSIP consultado
  desde Asterisk;
- soporte de varias cuentas por endpoint en la misma celda.

## Evidencia LAB

Test 68 run `34805839845` terminó PASS sobre
`feature/endpoint-credential-foundation`. La instalación del runtime, lint PHP,
verificación de esquema, smoke autenticado read-only del GRP2601P y verificación
final terminaron correctamente; `phone_write=NO` y `production_touched=NO`.

El operador validó visualmente la interfaz del Endpoint Configurator el
2026-09-13. La tabla mostró correctamente:

```text
GXP1630   192.168.1.169   extensión 201   Registered
GXP1625   192.168.1.168   extensión 202   Registered
J129      192.168.1.170   extensión 200   Registered
GRP2601P  192.168.1.176   extensión 203   Registered
```

## Target productivo

```text
Host:    cei-pbx02
PBX:     10.3.40.2
Runner:  github-runner-prod
Labels:  self-hosted, Linux, X64, j129-production, cei-pbx02
```

## Test 70 — preflight read-only

```text
70 | Ceiba Production | Endpoint Credentials | Read-Only Preflight
run: 35123613203
estado: PRODUCTION-SERVER-PASS
```

Marcadores principales:

```text
TEST70-PROD-RUNNER-GUARD-PASS
TEST70-HARNESS-INTEGRITY-PASS
TEST70-PROD-ENDPOINT-BASELINE-PASS
J129-PROD-FLEET-AUDIT-PASS
TEST70-PROD-WEB-HEALTH-PASS
TEST70-PROD-ENDPOINT-CREDENTIAL-PREFLIGHT=PASS
production_runtime_write=NO
endpointconfig_write=NO
phone_write=NO
```

Baseline preinstall aprobado:

```text
index.php              60bb6aaa461e72979cfd40551b9ef78e81c75656
reporte_endpoints.tpl  d979762079d4dcc2874759881104b3287fea71c2
javascript.js          44bea8adac8bd15d9b8548922d032fcf924edfc1
```

## Test 71 — instalación controlada

```text
71 | Ceiba Production | Endpoint Credentials | Controlled Runtime Install
run autoritativo: 35138230754
estado: PRODUCTION-SERVER-PASS
workflow head: c2946b390ae2f68529dff20fced9708765c5a44a
candidate: ef176c99935af5f833248358c4daf7b4ca0dde6a
helper blob: 3c16593a0f2490e00ad912838ec32eed2b35e26a
```

Runs previos seguros:

```text
35130705534  FAIL antes de preflight; ningún cambio productivo
35131492883  FAIL antes de preflight; helper productivo todavía ausente
35138230754  PASS autoritativo
```

El bootstrap único dejó:

```text
/usr/local/sbin/issabel-endpoint-credential-prod           root:root:0755
/etc/sudoers.d/issabel-endpoint-credential-prod            root:root:0440
```

El sudoers permite únicamente `preflight`, `install`, `verify` y
`rollback-runtime` con rutas/argumentos exactos. Los grants DDL permanentes se
limitan a `CREATE, ALTER, INDEX, REFERENCES` sobre las tres tablas nuevas y
`REFERENCES` sobre `endpoint`; sin `DROP`, `ALL PRIVILEGES`, `CREATE USER` ni DDL
general sobre `endpointconfig.*`.

### Resultado del run PASS

Preflight inmediatamente anterior a la escritura:

```text
TEST71-PAYLOAD-INTEGRITY-PASS
TEST71-WEB-HEALTH-PASS status=200
TEST71-LIMITED-DDL-GRANTS-PASS
TEST71-SCHEMA-STATE=ABSENT
TEST71-KEY-STATE=ABSENT
TEST71-PREINSTALL-BASELINE-PASS
TEST71-RUNTIME-STATE=ABSENT
phone_write=NO
TEST71-PREFLIGHT-PASS
```

Install y verificación:

```text
TEST71-BACKUP-MANIFEST-PASS
TEST71-SCHEMA-INSTALL-PASS
TEST71-SCHEMA-VERIFY-PASS
TEST71-KEY-INSTALL-PASS existing=NO
TEST71-PROD-ENDPOINT-CREDENTIAL-RUNTIME=PASS
TEST71-CONTROLLED-INSTALL-PASS
TEST71-WEB-HEALTH-PASS status=200
J129-PROD-FLEET-AUDIT-PASS
TEST71-PROD-CONTROLLED-INSTALL=PASS
phone_write=NO
```

Quedaron instalados server-side las tres tablas de credenciales, la clave externa
`root:asterisk:0640`, Vault, CLI productiva, `index.php`, diálogo `summary`,
`en.lang`, template y JavaScript del candidato. Antes de reemplazar archivos se
creó manifest/backup root-only. PHP/Apache pasaron lint, Apache recargó y HTTPS
local continuó en `200`.

El `fleet-audit` posterior conservó el inventario: 19 J129, 14 configurados, 12
registrados, 2 provisionados/no registrados y 5 `DETECTED_ONLY`. Test71 no
contactó ni reconfiguró teléfonos.

Evidencia sanitizada:

```text
artifact: test71-endpoint-credential-prod-35138230754
artifact id: 10464202042
sha256(zip): 63d4c189ca23574520b2783f2c333722c9333769a7993eff18a44befffbdc0d6
retención: 90 días
```

## Rollback

El rollback productivo es deliberadamente de **runtime**, no de datos.

```text
/usr/local/sbin/issabel-endpoint-credential-prod rollback-runtime \
  ROLLBACK-ENDPOINT-CREDENTIAL-RUNTIME-PROD
```

Restaura los archivos desde el manifest, valida Apache y recarga el servicio.
Las tablas y la clave se conservan. No ejecuta `DROP TABLE`, factory reset,
cambio de contraseña ni `Configure`.

## Secuencia actual

```text
LAB schema/runtime/visual PASS
-> Test 70 production read-only PASS (35123613203)
-> Test 71 controlled install PASS (35138230754)
-> validar UI productiva manualmente
-> canario de credencial real en una fase posterior separada
```
