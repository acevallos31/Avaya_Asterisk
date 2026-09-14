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
70. En este punto se documenta el contrato del gate; no existe todavía un
workflow activo ni se ha tocado producción.

## Test 70 — preflight read-only reservado

Nombre normalizado:

```text
70 | Ceiba Production | Endpoint Credentials | Read-Only Preflight
```

El workflow futuro deberá ser `workflow_dispatch` manual y exigir confirmación
exacta:

```text
PREFLIGHT-ENDPOINT-CREDENTIALS-PROD
```

Debe abortar si el host, usuario, rama o labels no corresponden a producción.
No debe conceder sudo nuevo: reutilizará únicamente el helper productivo
root-owned ya instalado `avaya-j129-prod-validation` para auditorías read-only.

El preflight deberá validar:

1. auditorías estáticas de la fundación de credenciales y del resumen de
   cuentas/registro;
2. identidad exacta `github-runner-prod@cei-pbx02`;
3. integridad y disponibilidad del helper productivo existente;
4. release J129 v0.1.0 congelada y salud base de la PBX mediante `audit`;
5. inventario Avaya/registro mediante `fleet-audit`, sin secretos;
6. ausencia de drift en `index.php`, `reporte_endpoints.tpl` y `javascript.js`
   frente a la rama `Audit`, antes de sobrescribirlos;
7. estado HTTP local de Issabel sin respuestas 5xx;
8. presencia/ausencia informativa de los nuevos paths del runtime, sin
   modificarlos;
9. evidencia sanitizada con retención de 90 días.

Marcadores previstos:

```text
TEST70-PROD-RUNNER-GUARD-PASS
TEST70-PROD-ENDPOINT-BASELINE-PASS
J129-PROD-SERVER-AUDIT-PASS
J129-PROD-FLEET-AUDIT-PASS
TEST70-PROD-WEB-HEALTH-PASS
TEST70-PROD-ENDPOINT-CREDENTIAL-PREFLIGHT=PASS
production_runtime_write=NO
endpointconfig_write=NO
phone_write=NO
```

Cualquier drift de los tres archivos live debe bloquear el despliegue. No se
debe forzar la instalación hasta explicar la diferencia.

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
-> implementar Test 70 read-only
-> ejecutar Test 70 en Ceiba
-> revisar drift / salud / inventario
-> preparar e instalar helper productivo dedicado
-> Test 71 controlled runtime install
-> validar UI productiva
-> canario de credencial en una fase posterior separada
```
