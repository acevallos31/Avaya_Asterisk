# Endpoint Configurator — plan de despliegue a producción

Fecha de preparación: 2026-09-14.

## Alcance del candidato

Este gate cubre exclusivamente la fundación de credenciales administrativas del
Endpoint Configurator y la visualización de cuentas/registro en la tabla
principal. No autoriza firmware, reset, `Configure`, cambio de extensión ni
escritura a teléfonos.

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

## Evidencia LAB que habilita el preflight productivo

Test 68 run `34805839845` terminó PASS sobre
`feature/endpoint-credential-foundation`. La instalación del runtime, lint PHP,
verificación de esquema, smoke autenticado read-only del GRP2601P y verificación
final terminaron correctamente; `phone_write=NO` y `production_touched=NO`.

El operador validó visualmente la interfaz del Endpoint Configurator el
2026-09-13 (hora local). La tabla mostró correctamente cuatro endpoints con sus
cuentas y estado registrado:

```text
GXP1630   192.168.1.169   extensión 201   Registered
GXP1625   192.168.1.168   extensión 202   Registered
J129      192.168.1.170   extensión 200   Registered
GRP2601P  192.168.1.176   extensión 203   Registered
```

Esta evidencia cierra la validación visual LAB de la nueva columna. No sustituye
el preflight ni autoriza todavía la instalación en producción.

## Target productivo

```text
Host:    cei-pbx02
PBX:     10.3.40.2
Runner:  github-runner-prod
Labels:  self-hosted, Linux, X64, j129-production, cei-pbx02
```

La primera ejecución productiva será **read-only** y queda reservada como Test
70.

## Test 70 — preflight read-only

Nombre normalizado:

```text
70 | Ceiba Production | Endpoint Credentials | Read-Only Preflight
```

Estado actual: `HARNESS-STAGED`. El harness read-only quedó versionado en:

```text
scripts/prod-endpoint-credential-preflight.sh
commit: 207c58e315e36184091ed5cd37080842434215ab
blob:   7545b2e14981da8ca07446ef2ec8d6200ddf4f9b
```

El script no instala archivos, no ejecuta migraciones, no modifica
`endpointconfig`, no contacta teléfonos y no llama `Configure`. Solo usa el
helper productivo root-owned existente en la acción read-only `fleet-audit`.

### Baseline inmutable para detección de drift

El candidato nació del commit exacto de Audit:

```text
ce90056c652c7e3a280fc8a1416580e6172dcc01
```

Test 70 compara los tres archivos live que posteriormente serían reemplazados
contra sus Git blob SHA exactos de ese baseline:

```text
index.php                                b68103a3c28265b3ef2619f663b0f6ed87ffa89f
reporte_endpoints.tpl                    d979762079d4dcc2874759881104b3287fea71c2
javascript.js                            44bea8adac8bd15d9b8548922d032fcf924edfc1
```

La comparación usa `git hash-object` y nunca imprime el contenido de los
archivos. Cualquier diferencia produce `TEST70-DRIFT-BLOCK` y detiene el gate.
No se debe forzar un deploy hasta explicar ese drift.

### Controles incluidos en el harness

1. identidad exacta `github-runner-prod@cei-pbx02`;
2. helper `/usr/local/sbin/avaya-j129-prod-validation` presente como
   `root:root:755` y allowlisted en sudoers;
3. ausencia de drift en `index.php`, `reporte_endpoints.tpl` y
   `javascript.js` contra el baseline inmutable;
4. inventario Avaya/registro mediante `fleet-audit`, sin secretos;
5. salud HTTPS local de Issabel sin respuesta 5xx;
6. inventario informativo de los paths nuevos del runtime, sin crearlos ni
   modificarlos;
7. reporte sanitizado en `/tmp/test70-endpoint-credential-preflight.txt`.

Marcadores esperados:

```text
TEST70-PROD-RUNNER-GUARD-PASS
TEST70-PROD-ENDPOINT-BASELINE-PASS
J129-PROD-FLEET-AUDIT-PASS
TEST70-PROD-WEB-HEALTH-PASS
TEST70-PROD-ENDPOINT-CREDENTIAL-PREFLIGHT=PASS
production_runtime_write=NO
endpointconfig_write=NO
phone_write=NO
```

### Wrapper de GitHub Actions pendiente

El harness ya está preparado, pero el workflow
`.github/workflows/prod-endpoint-credential-test70.yml` todavía no está activo.
El wrapper final debe vivir en `main`, ser `workflow_dispatch`, exigir la
confirmación exacta:

```text
PREFLIGHT-ENDPOINT-CREDENTIALS-PROD
```

y usar el runner exacto:

```yaml
runs-on: [self-hosted, Linux, X64, j129-production, cei-pbx02]
```

El wrapper debe ejecutar primero la auditoría productiva existente de la release
J129 congelada y después ejecutar **el harness pinneado por commit/blob**, no una
versión flotante tomada de una rama. No debe ampliar sudo ni instalar helpers.

## Gate posterior — Test 71

Test 71 **no se ejecuta ni se considera autorizado** hasta que Test 70 termine
PASS y se revise su evidencia.

El diseño previsto para Test 71 es una instalación controlada con:

- helper productivo dedicado, root-owned e instalado una sola vez; el runner no
  podrá autoactualizar ese helper desde el workspace público;
- sudoers limitado a acciones allowlisted del helper, nunca shell root genérico;
- backup/manifest previo de cada archivo reemplazado;
- aplicación idempotente del esquema de credenciales;
- creación/preservación de la clave externa con `root:asterisk:0640`;
- instalación de runtime + `apachectl -t` + reload de Apache;
- verificación inmediata y rollback de archivos si falla el runtime;
- cero contacto con teléfonos durante la instalación;
- validación manual de la UI antes de almacenar o aplicar una credencial real.

El helper de producción será distinto del sincronizador LAB: producción no debe
permitir que un checkout del repositorio reemplace por sí mismo un ejecutable
root-owned.

## Rollback

El rollback inicial de producción será de **runtime**, no de datos. Las tablas y
la clave no se eliminan automáticamente si ya pudieron contener credenciales o
eventos. La restauración debe usar el manifest creado antes del primer install y
volver a validar Apache antes del reload.

No se ejecutará `DROP TABLE`, factory reset, cambio de contraseña o `Configure`
como parte del rollback de runtime.

## Secuencia acordada

```text
LAB visual PASS
-> harness Test 70 read-only STAGED
-> activar wrapper Test 70 en main
-> ejecutar Test 70 en Ceiba
-> revisar drift / salud / inventario
-> preparar e instalar helper productivo dedicado
-> Test 71 controlled runtime install
-> validar UI productiva
-> canario de credencial en una fase posterior separada
```
