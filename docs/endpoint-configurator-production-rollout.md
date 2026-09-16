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

Nombre:

```text
70 | Ceiba Production | Endpoint Credentials | Read-Only Preflight
```

Estado: **CERRADO / PRODUCTION-SERVER-PASS**.

Run autoritativo:

```text
35123613203
```

Resultado confirmado:

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

La salud HTTPS local fue `200`. El inventario previo confirmó que la nueva
clave, Vault, diálogo `summary` y CLI productiva todavía estaban ausentes.

### Baseline revisado de Ceiba

Los primeros runs de Test 70 detectaron que `index.php` productivo difería del
commit Audit únicamente en la forma de cargar librerías. Se auditó el diff y se
aprobó el archivo productivo exacto, sin wildcard ni relajación del gate.

Baselines de preinstalación aceptados:

```text
index.php                                60bb6aaa461e72979cfd40551b9ef78e81c75656
reporte_endpoints.tpl                    d979762079d4dcc2874759881104b3287fea71c2
javascript.js                            44bea8adac8bd15d9b8548922d032fcf924edfc1
```

El `index.php` usa el blob exacto revisado de Ceiba; template y JavaScript
continúan contra la referencia Audit `ce90056c652c7e3a280fc8a1416580e6172dcc01`.
La comparación se realiza como Git blob SHA-1 calculado con Python, sin depender
de `git` instalado en el runner.

La flota observada en el run PASS fue 19 Avaya J129: 14 configurados, 12
registrados, 2 provisionados/no registrados y 5 `DETECTED_ONLY`. Esa auditoría
es inventario y no implica escritura a teléfonos.

## Test 71 — instalación controlada

Nombre:

```text
71 | Ceiba Production | Endpoint Credentials | Controlled Runtime Install
```

Estado: **STAGED / NOT-TESTED**.

Workflow manual-only activo en `main`:

```text
.github/workflows/prod-endpoint-credential-test71.yml
main commit: 58fe365413481ffbdd7317617062ddd9129b13a6
```

Candidato inmutable del workflow:

```text
candidate commit: 6fc9334130b8867d7dc1722bfe35fd895e30d321
helper blob:      6e3a8b63253a4a2477340f5d6522b4a6481f2ebf
```

Helper dedicado:

```text
deploy/endpoint-configurator/bin/endpoint-credential-prod-deploy
instalación final: /usr/local/sbin/issabel-endpoint-credential-prod
owner/mode: root:root:0755
```

Sudoers restringido:

```text
deploy/endpoint-configurator/sudoers/issabel-endpoint-credential-prod
instalación final: /etc/sudoers.d/issabel-endpoint-credential-prod
owner/mode: root:root:0440
```

El helper no puede autoactualizarse desde el workspace público. Acepta únicamente
el root exacto `_test71_candidate`, valida cada archivo por Git blob SHA y
rechaza symlinks o propietario inesperado. El sudoers permite únicamente cuatro
formas exactas: `preflight`, `install`, `verify` y rollback de runtime con
confirmación explícita.

### Bootstrap único previo

Antes del primer run de Test 71 hay que instalar manualmente el helper y el
sudoers root-owned una sola vez. Procedimiento exacto:

```text
docs/endpoint-configurator-prod-helper-bootstrap.md
```

Este bootstrap **no** instala runtime, no modifica DB y no contacta teléfonos.
No se repetirá el ciclo de conceder/retirar sudo por cada despliegue: queda una
allowlist persistente, estrecha y específica para este helper.

### Confirmación para ejecutar Test 71

```text
INSTALL-ENDPOINT-CREDENTIALS-PROD
```

### Controles del install

1. workflow solo manual desde `main` y runner exacto de Ceiba;
2. candidate commit y helper blob pinneados;
3. revalidación del baseline productivo inmediatamente antes de escribir;
4. `apachectl -t` y salud HTTPS antes del install;
5. esquema: acepta solo estado `0/3` o `3/3`; un esquema parcial aborta;
6. el SQL se aplica usando la cuenta DB local configurada por Issabel; el helper
   no concede privilegios ni abre DDL global;
7. creación/preservación de la clave externa `root:asterisk:0640`;
8. manifest y backup root-only antes de reemplazar runtime;
9. instalación de Vault, CLI, `index.php`, diálogo `summary`, template y JS con
   modos fijos;
10. `apachectl -t`, reload y verificación byte a byte contra el candidato;
11. verificación de las tres tablas y salud HTTPS;
12. `fleet-audit` read-only posterior;
13. evidencia sanitizada como artifact por 90 días;
14. `phone_write=NO` durante todo Test 71.

## Rollback

El rollback productivo es deliberadamente de **runtime**, no de datos.

Si el install falla después de comenzar a reemplazar archivos, el helper restaura
los archivos desde el manifest, valida Apache y hace reload. Las tablas y la
clave se conservan. No se ejecuta `DROP TABLE`, factory reset, cambio de
contraseña ni `Configure`.

Rollback manual, solo si se autoriza explícitamente:

```text
/usr/local/sbin/issabel-endpoint-credential-prod rollback-runtime \
  ROLLBACK-ENDPOINT-CREDENTIAL-RUNTIME-PROD
```

El runner solo puede invocar esa forma exacta mediante sudoers.

## Secuencia actual

```text
LAB schema/runtime/visual PASS
-> Test 70 production read-only PASS (35123613203)
-> Test 71 helper/workflow STAGED
-> bootstrap único helper + sudoers en cei-pbx02
-> ejecutar Test 71 controlled install
-> validar UI productiva manualmente
-> canario de credencial real en una fase posterior separada
```
